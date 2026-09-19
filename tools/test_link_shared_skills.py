from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOKS = Path(__file__).parents[1] / "hooks" / "os"


class LinkSharedSkillsIntoCodexTest(unittest.TestCase):
    """skills.sh only wires the ~/.agents store into Claude Code; Codex needs the
    same skills under ${CODEX_HOME}/skills or it sees none of them."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.store = self.home / ".agents" / "skills"
        self.store.mkdir(parents=True)

    def add_skill(self, name: str, with_doc: bool = True) -> Path:
        path = self.store / name
        path.mkdir(parents=True)
        if with_doc:
            (path / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\n---\n", encoding="utf-8"
            )
        return path

    def link(self, codex_home: str | None = None) -> subprocess.CompletedProcess:
        environment = dict(os.environ, HOME=str(self.home))
        environment.pop("CODEX_HOME", None)
        if codex_home is not None:
            environment["CODEX_HOME"] = codex_home
        return subprocess.run(
            [
                "bash",
                "-c",
                f'source "{HOOKS}" >/dev/null 2>&1; '
                "tools::link_shared_skills_into_codex",
            ],
            env=environment,
            capture_output=True,
            text=True,
        )

    def codex_link(self, name: str) -> Path:
        return self.home / ".codex" / "skills" / name

    def test_links_every_store_skill_into_codex(self) -> None:
        expected = {name: self.add_skill(name) for name in ("grilling", "simple-english")}
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, source in expected.items():
            link = self.codex_link(name)
            self.assertTrue(link.is_symlink(), f"{link} should be a symlink")
            self.assertEqual(link.resolve(), source.resolve())

    def test_discovers_the_store_without_a_manifest(self) -> None:
        # A skill added by hand with `npx skills add <repo>` is not in
        # AI_SKILL_SOURCES, and must still reach Codex.
        self.add_skill("added-by-hand")
        self.link()
        self.assertTrue(self.codex_link("added-by-hand").is_symlink())

    def test_both_agents_read_the_same_file(self) -> None:
        self.add_skill("simple-english")
        self.link()
        # One copy in the store: an upstream refresh must be visible through the
        # Codex link with nothing to re-install.
        (self.store / "simple-english" / "SKILL.md").write_text(
            "refreshed\n", encoding="utf-8"
        )
        self.assertEqual(
            (self.codex_link("simple-english") / "SKILL.md").read_text(encoding="utf-8"),
            "refreshed\n",
        )

    def test_skips_a_directory_with_no_skill_md(self) -> None:
        self.add_skill("incomplete", with_doc=False)
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.codex_link("incomplete").exists())
        self.assertIn("incomplete", result.stdout + result.stderr)

    def test_honours_a_relocated_codex_home(self) -> None:
        expected = self.add_skill("simple-english")
        elsewhere = self.root / "elsewhere"
        result = self.link(codex_home=str(elsewhere))
        self.assertEqual(result.returncode, 0, result.stderr)
        link = elsewhere / "skills" / "simple-english"
        self.assertTrue(link.is_symlink(), f"{link} should be a symlink")
        # A $HOME-relative target would dangle from a non-default CODEX_HOME.
        self.assertEqual(link.resolve(), expected.resolve())

    def test_is_idempotent(self) -> None:
        self.add_skill("simple-english")
        self.link()
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.codex_link("simple-english").is_symlink())

    def test_relinks_a_stale_link(self) -> None:
        expected = self.add_skill("simple-english")
        self.link()
        link = self.codex_link("simple-english")
        link.unlink()
        link.symlink_to("/nonexistent/simple-english")
        self.link()
        self.assertEqual(link.resolve(), expected.resolve())

    def test_prunes_a_link_whose_store_entry_is_gone(self) -> None:
        # `skills remove -g -s <name>` empties the store but leaves the Codex
        # link, and Codex then reads a skill directory with no SKILL.md.
        skill = self.add_skill("simple-english")
        self.link()
        for child in skill.iterdir():
            child.unlink()
        skill.rmdir()
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)
        link = self.codex_link("simple-english")
        self.assertFalse(link.is_symlink(), f"{link} should have been pruned")

    def test_prunes_a_legacy_relative_link(self) -> None:
        # The earlier implementation wrote $HOME-relative targets; those are
        # still ours to clean up.
        codex_skills = self.home / ".codex" / "skills"
        codex_skills.mkdir(parents=True)
        (codex_skills / "grilling").symlink_to("../../.agents/skills/grilling")
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((codex_skills / "grilling").is_symlink())

    def test_leaves_a_link_outside_the_store_alone(self) -> None:
        # skills/<name> in this repo is linked by tools::install_local_skills;
        # pruning it would uninstall a skill this repo owns.
        local = self.root / "dotfiles" / "skills" / "ci-remote"
        local.mkdir(parents=True)
        codex_skills = self.home / ".codex" / "skills"
        codex_skills.mkdir(parents=True)
        (codex_skills / "ci-remote").symlink_to(local)
        self.link()
        self.assertEqual((codex_skills / "ci-remote").resolve(), local.resolve())

    def test_leaves_a_real_directory_alone(self) -> None:
        # Codex-only skills that were never in the store live here as real
        # directories.
        codex_skills = self.home / ".codex" / "skills"
        codex_skills.mkdir(parents=True)
        native = codex_skills / "harness-generation"
        native.mkdir()
        (native / "SKILL.md").write_text("native\n", encoding="utf-8")
        self.link()
        self.assertTrue((native / "SKILL.md").is_file())

    def test_missing_store_is_not_fatal(self) -> None:
        self.store.rmdir()
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / ".codex" / "skills").exists())

    def test_empty_store_is_not_fatal(self) -> None:
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
