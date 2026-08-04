from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOKS = Path(__file__).parents[1] / "hooks" / "os"


class InstallLocalSkillsTest(unittest.TestCase):
    """Skills authored in this repo must land in BOTH agents from one source."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.source = self.root / "skills"
        self.home.mkdir()
        self.source.mkdir()

    def add_skill(self, name: str, with_doc: bool = True) -> Path:
        path = self.source / name
        path.mkdir(parents=True)
        if with_doc:
            (path / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\n---\n", encoding="utf-8"
            )
        return path

    def install(self) -> subprocess.CompletedProcess:
        environment = dict(os.environ, HOME=str(self.home))
        environment.pop("CODEX_HOME", None)
        return subprocess.run(
            [
                "bash",
                "-c",
                f'source "{HOOKS}" >/dev/null 2>&1; '
                f'tools::install_local_skills "{self.source}"',
            ],
            env=environment,
            capture_output=True,
            text=True,
        )

    def claude_link(self, name: str) -> Path:
        return self.home / ".claude" / "skills" / name

    def codex_link(self, name: str) -> Path:
        return self.home / ".codex" / "skills" / name

    def test_links_a_skill_into_both_agents(self) -> None:
        expected = self.add_skill("ci-remote")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        for link in (self.claude_link("ci-remote"), self.codex_link("ci-remote")):
            self.assertTrue(link.is_symlink(), f"{link} should be a symlink")
            self.assertEqual(link.resolve(), expected.resolve())

    def test_both_agents_read_the_same_file(self) -> None:
        self.add_skill("ci-remote")
        self.install()
        # One source of truth: an edit must be visible through both links.
        (self.source / "ci-remote" / "SKILL.md").write_text("edited\n", encoding="utf-8")
        for link in (self.claude_link("ci-remote"), self.codex_link("ci-remote")):
            self.assertEqual(
                (link / "SKILL.md").read_text(encoding="utf-8"), "edited\n"
            )

    def test_discovers_every_directory_without_a_manifest(self) -> None:
        for name in ("alpha", "beta", "gamma"):
            self.add_skill(name)
        self.install()
        for name in ("alpha", "beta", "gamma"):
            self.assertTrue(self.claude_link(name).is_symlink(), name)
            self.assertTrue(self.codex_link(name).is_symlink(), name)

    def test_skips_a_directory_with_no_skill_md(self) -> None:
        self.add_skill("incomplete", with_doc=False)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.claude_link("incomplete").exists())
        self.assertFalse(self.codex_link("incomplete").exists())
        self.assertIn("incomplete", result.stdout + result.stderr)

    def test_refuses_to_shadow_a_third_party_skill(self) -> None:
        self.add_skill("research")
        store = self.home / ".agents" / "skills" / "research"
        store.mkdir(parents=True)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            self.claude_link("research").exists(),
            "must not silently override the third-party skill store",
        )

    def test_is_idempotent(self) -> None:
        self.add_skill("ci-remote")
        self.install()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.claude_link("ci-remote").is_symlink())

    def test_relinks_when_the_source_moves(self) -> None:
        self.add_skill("ci-remote")
        self.install()
        # A stale link from an earlier layout must be replaced, not left behind.
        link = self.claude_link("ci-remote")
        link.unlink()
        link.symlink_to("/nonexistent/ci-remote")
        self.install()
        self.assertEqual(link.resolve(), (self.source / "ci-remote").resolve())

    def test_succeeds_when_there_are_no_skills(self) -> None:
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_source_directory_is_not_fatal(self) -> None:
        self.source.rmdir()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
