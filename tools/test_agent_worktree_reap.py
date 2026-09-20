"""Tests for bin/agent-worktree-reap.

The reaper deletes directories, so every safety rule gets a test that proves it
refuses. A guard that cannot be shown to fire is not a guard.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "bin" / "agent-worktree-reap"


def load_module():
    loader = importlib.machinery.SourceFileLoader("agent_worktree_reap", str(SCRIPT))
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    return module


reap = load_module()


def run_git(cwd, *args, check=True):
    return subprocess.run(
        ("git", "-C", str(cwd)) + args,
        capture_output=True, text=True, check=check,
    )


class WorktreeFixture(unittest.TestCase):
    """A real git repository with real worktrees; no git mocking.

    Holds no tests of its own so subclasses do not re-run each other's.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run_git(self.repo, "init", "-q", "-b", "main")
        run_git(self.repo, "config", "user.email", "test@example.invalid")
        run_git(self.repo, "config", "user.name", "Test")
        run_git(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "file.txt").write_text("base\n")
        run_git(self.repo, "add", "file.txt")
        self.commit(self.repo, "base", days_ago=400)
        self.agent_root = self.repo / ".worktrees"
        self.rescue_dir = self.root / "rescue"

    def tearDown(self):
        self.tmp.cleanup()

    def add_worktree(self, name, *, root=None, branch=None):
        base = Path(root) if root else self.agent_root
        path = base / name
        run_git(self.repo, "worktree", "add", "-q", "-b", branch or name, str(path))
        return path

    def commit(self, path, message, *, days_ago=400):
        """Commit with a backdated author AND committer date.

        The reaper ages a worktree by the NEWEST of its mtimes and its HEAD
        commit date, so a fixture cannot look idle while its commit is fresh.
        """
        stamp = f"{int(time.time()) - int(days_ago * 86400)} +0000"
        env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        subprocess.run(
            ("git", "-C", str(path), "commit", "-qm", message),
            env=env, capture_output=True, text=True, check=True,
        )

    def age(self, path, days):
        """Backdate the checkout mtimes. HEAD is already old from setUp."""
        past = int(time.time()) - int(days * 86400)
        for target in (path, path / ".git"):
            os.utime(target, (past, past))

    def reap(self, *extra, expect=0):
        cmd = ["python3", str(SCRIPT), "--repo", str(self.repo), "--json", *extra]
        # Pin the agent roots: TMPDIR may itself sit inside a default root.
        env = dict(os.environ, **{reap.ROOTS_ENV: str(self.agent_root)})
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False,
                              env=env)
        self.assertEqual(proc.returncode, expect, proc.stderr)
        return json.loads(proc.stdout)

    def reasons(self, report):
        return {e["path"]: e["reason"] for e in report["skipped"]}


class ReaperTestCase(WorktreeFixture):
    # --- the happy path -------------------------------------------------

    def test_removes_old_clean_agent_worktree_and_keeps_its_branch(self):
        path = self.add_worktree("old", branch="agent/old")
        self.age(path, 30)
        report = self.reap()
        self.assertEqual([e["path"] for e in report["removed"]], [str(path)])
        self.assertFalse(path.exists())
        branches = run_git(self.repo, "branch", "--list", "agent/old").stdout
        self.assertIn("agent/old", branches,
                      "removing a worktree must never delete its branch")

    def test_commits_survive_removal(self):
        path = self.add_worktree("withcommit", branch="agent/withcommit")
        (path / "new.txt").write_text("work\n")
        run_git(path, "add", "new.txt")
        self.commit(path, "unpushed work", days_ago=400)
        sha = run_git(path, "rev-parse", "HEAD").stdout.strip()
        self.age(path, 30)
        self.reap()
        self.assertFalse(path.exists())
        # The object must still be reachable from the retained branch.
        self.assertEqual(
            run_git(self.repo, "rev-parse", "agent/withcommit").stdout.strip(), sha
        )
        run_git(self.repo, "cat-file", "-e", f"{sha}^{{commit}}")

    # --- each refusal ---------------------------------------------------

    def test_keeps_worktree_newer_than_age(self):
        path = self.add_worktree("fresh")
        self.age(path, 1)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertIn("active", self.reasons(report)[str(path)])
        self.assertTrue(path.exists())

    def test_keeps_worktree_outside_agent_roots(self):
        outside = self.root / "mine"
        outside.mkdir()
        path = self.add_worktree("handmade", root=outside)
        self.age(path, 400)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertEqual(self.reasons(report)[str(path)], "outside agent roots")
        self.assertTrue(path.exists())

    def test_keeps_dirty_worktree_without_rescue(self):
        path = self.add_worktree("dirty")
        (path / "file.txt").write_text("modified\n")
        self.age(path, 30)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertIn("uncommitted work", self.reasons(report)[str(path)])
        self.assertTrue(path.exists())

    def test_keeps_worktree_with_untracked_file_without_rescue(self):
        path = self.add_worktree("untracked")
        (path / "scratch.md").write_text("notes\n")
        self.age(path, 30)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertIn("untracked", self.reasons(report)[str(path)])
        self.assertTrue(path.exists())

    def test_keeps_main_checkout(self):
        report = self.reap()
        self.assertEqual(self.reasons(report)[str(self.repo)], "main checkout")
        self.assertTrue((self.repo / "file.txt").exists())

    def test_keeps_locked_worktree(self):
        path = self.add_worktree("locked")
        run_git(self.repo, "worktree", "lock", str(path))
        self.age(path, 30)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertEqual(self.reasons(report)[str(path)], "locked")
        self.assertTrue(path.exists())

    def test_keeps_worktree_held_by_a_running_process(self):
        path = self.add_worktree("inuse")
        self.age(path, 30)
        proc = subprocess.Popen(["sleep", "30"], cwd=str(path))
        try:
            report = self.reap()
            self.assertEqual(report["removed"], [])
            self.assertEqual(self.reasons(report)[str(path)],
                             "in use by a running process")
            self.assertTrue(path.exists())
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    def test_ignored_files_do_not_block_removal(self):
        path = self.add_worktree("ignored")
        (path / ".gitignore").write_text("build/\n")
        run_git(path, "add", ".gitignore")
        self.commit(path, "ignore build", days_ago=400)
        (path / "build").mkdir()
        (path / "build" / "artifact.bin").write_text("junk\n")
        self.age(path, 30)
        report = self.reap()
        self.assertEqual([e["path"] for e in report["removed"]], [str(path)])
        self.assertFalse(path.exists())

    # --- rescue ---------------------------------------------------------

    def test_rescue_captures_then_removes(self):
        path = self.add_worktree("rescueme")
        (path / "file.txt").write_text("edited\n")
        (path / "extra.txt").write_text("untracked\n")
        self.age(path, 30)
        report = self.reap("--rescue", str(self.rescue_dir))
        self.assertEqual([e["path"] for e in report["removed"]], [str(path)])
        self.assertFalse(path.exists())
        entries = list(self.rescue_dir.iterdir())
        self.assertEqual(len(entries), 1)
        patch = (entries[0] / "tracked.patch").read_text()
        self.assertIn("edited", patch)
        self.assertTrue((entries[0] / "untracked.tar.gz").exists())
        meta = json.loads((entries[0] / "meta.json").read_text())
        self.assertEqual(meta["path"], str(path))
        self.assertEqual(meta["untracked"], 1)

    def test_rescued_patch_restores_the_edit(self):
        path = self.add_worktree("restoreme")
        (path / "file.txt").write_text("precious change\n")
        self.age(path, 30)
        self.reap("--rescue", str(self.rescue_dir))
        entry = next(self.rescue_dir.iterdir())
        restored = self.add_worktree("restored", branch="restored-branch")
        run_git(restored, "checkout", "-q", "restoreme")
        run_git(restored, "apply", str(entry / "tracked.patch"))
        self.assertEqual((restored / "file.txt").read_text(), "precious change\n")

    # --- dry run --------------------------------------------------------

    def test_dry_run_changes_nothing(self):
        path = self.add_worktree("dry")
        self.age(path, 30)
        report = self.reap("--dry-run")
        self.assertEqual([e["path"] for e in report["removed"]], [str(path)])
        self.assertTrue(path.exists(), "--dry-run must not delete")
        listed = run_git(self.repo, "worktree", "list").stdout
        self.assertIn(str(path), listed, "--dry-run must not deregister")

    def test_dry_run_does_not_write_rescue_files(self):
        path = self.add_worktree("drydirty")
        (path / "file.txt").write_text("edited\n")
        self.age(path, 30)
        self.reap("--dry-run", "--rescue", str(self.rescue_dir))
        self.assertTrue(path.exists())
        self.assertFalse(self.rescue_dir.exists())

    # --- the traps this tool exists to survive --------------------------

    def test_removes_worktree_containing_read_only_directories(self):
        """setup-envtest writes asset dirs read-only; rm fails until chmod."""
        path = self.add_worktree("readonly")
        (path / ".gitignore").write_text("bin/\n")
        run_git(path, "add", ".gitignore")
        self.commit(path, "ignore bin", days_ago=400)
        assets = path / "bin" / "envtest-assets" / "k8s"
        assets.mkdir(parents=True)
        (assets / "kube-apiserver").write_text("binary\n")
        self.age(path, 30)
        os.chmod(assets, 0o555)
        try:
            report = self.reap()
            self.assertEqual(report["failed"], [])
            self.assertEqual([e["path"] for e in report["removed"]], [str(path)])
            self.assertFalse(path.exists())
        finally:
            if assets.exists():
                os.chmod(assets, 0o755)

    def test_age_uses_newest_signal_so_recent_commits_protect(self):
        """A backdated directory with a fresh commit is still active."""
        path = self.add_worktree("freshcommit")
        (path / "file.txt").write_text("touched\n")
        run_git(path, "add", "file.txt")
        run_git(path, "commit", "-qm", "recent")  # deliberately fresh
        self.age(path, 400)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertIn("active", self.reasons(report)[str(path)])
        self.assertTrue(path.exists())

    def test_missing_path_is_reported_not_removed(self):
        path = self.add_worktree("vanished")
        self.age(path, 30)
        import shutil as _shutil
        _shutil.rmtree(path)
        report = self.reap()
        self.assertEqual(report["removed"], [])
        self.assertIn("path missing", self.reasons(report)[str(path)])


class HelpersTestCase(unittest.TestCase):
    def test_is_under_rejects_sibling_prefix(self):
        self.assertTrue(reap.is_under("/a/b/c", "/a/b"))
        self.assertTrue(reap.is_under("/a/b", "/a/b"))
        self.assertFalse(reap.is_under("/a/bc", "/a/b"),
                         "a shared name prefix is not containment")
        self.assertFalse(reap.is_under("/a", "/a/b"))

    def test_default_age_is_longer_than_an_agent_lifetime(self):
        self.assertGreaterEqual(reap.DEFAULT_AGE_DAYS, 7)


if __name__ == "__main__":
    unittest.main()


class RescueRetentionTestCase(WorktreeFixture):
    """The rescue store must not become the next unbounded directory."""

    def test_expired_rescue_entries_are_dropped(self):
        stale = self.rescue_dir / "old-deadbeef"
        stale.mkdir(parents=True)
        (stale / "tracked.patch").write_text("stale\n")
        past = int(time.time()) - int(200 * 86400)
        for target in (stale / "tracked.patch", stale):
            os.utime(target, (past, past))

        path = self.add_worktree("fresh-dirty")
        (path / "file.txt").write_text("edited\n")
        self.age(path, 30)
        report = self.reap("--rescue", str(self.rescue_dir))

        self.assertEqual(report["rescue_pruned"], [str(stale)])
        self.assertFalse(stale.exists())
        # The entry written by this very run must survive.
        self.assertEqual(len(list(self.rescue_dir.iterdir())), 1)

    def test_recent_rescue_entries_are_kept(self):
        recent = self.rescue_dir / "recent-cafebabe"
        recent.mkdir(parents=True)
        (recent / "tracked.patch").write_text("recent\n")
        path = self.add_worktree("another")
        self.age(path, 30)
        report = self.reap("--rescue", str(self.rescue_dir))
        self.assertEqual(report["rescue_pruned"], [])
        self.assertTrue(recent.exists())

    def test_zero_retention_keeps_everything(self):
        stale = self.rescue_dir / "ancient-0000"
        stale.mkdir(parents=True)
        (stale / "tracked.patch").write_text("ancient\n")
        past = int(time.time()) - int(9999 * 86400)
        for target in (stale / "tracked.patch", stale):
            os.utime(target, (past, past))
        path = self.add_worktree("yetanother")
        self.age(path, 30)
        report = self.reap("--rescue", str(self.rescue_dir),
                           "--rescue-retain-days", "0")
        self.assertEqual(report["rescue_pruned"], [])
        self.assertTrue(stale.exists())

    def test_dry_run_does_not_prune_the_rescue_store(self):
        stale = self.rescue_dir / "old-feedface"
        stale.mkdir(parents=True)
        (stale / "tracked.patch").write_text("stale\n")
        past = int(time.time()) - int(200 * 86400)
        for target in (stale / "tracked.patch", stale):
            os.utime(target, (past, past))
        path = self.add_worktree("drytoo")
        self.age(path, 30)
        report = self.reap("--dry-run", "--rescue", str(self.rescue_dir))
        self.assertEqual(report["rescue_pruned"], [])
        self.assertTrue(stale.exists())
