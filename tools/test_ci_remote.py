from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "ci-remote"


def load_module():
    """Import bin/ci-remote, which has no .py suffix, as a module."""
    loader = SourceFileLoader("ci_remote", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    # @dataclass resolves annotations through sys.modules, so register first.
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


ci = load_module()


WORKFLOW = textwrap.dedent(
    """
    name: Pull Request
    on:
      pull_request:
        types: [opened]
    env:
      GLOBAL: workflow
    jobs:
      Static:
        runs-on: ubuntu-latest
        env:
          SCOPE: job
        steps:
        - name: Checkout
          uses: actions/checkout@v5
        - name: Setup Go
          uses: ./.github/actions/go-cache
        - name: Lint
          run: make lint
        - name: Format check
          continue-on-error: true
          run: make lint-fmt
      Unit:
        runs-on: ubuntu-latest
        steps:
        - name: Checkout
          uses: actions/checkout@v5
        - name: Unit tests
          run: |
            echo first
            make test-unit
      Report:
        needs: [Static, Unit]
        runs-on: ubuntu-latest
        steps:
        - name: Report
          run: echo done
    """
).lstrip()


def write_workflow(root: Path, body: str = WORKFLOW, name: str = "pull-request.yaml") -> Path:
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


class WorkflowParsingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.workflow = write_workflow(self.root)

    def jobs(self):
        return {job.key: job for job in ci.parse_workflow(self.workflow)}

    def test_keeps_only_run_steps(self) -> None:
        static = self.jobs()["Static"]
        self.assertEqual([step.name for step in static.steps], ["Lint", "Format check"])

    def test_reports_skipped_uses_steps(self) -> None:
        static = self.jobs()["Static"]
        self.assertEqual(len(static.skipped_uses), 2)
        self.assertIn("actions/checkout@v5", static.skipped_uses[0])

    def test_marks_continue_on_error_steps_advisory(self) -> None:
        static = self.jobs()["Static"]
        self.assertFalse(static.steps[0].continue_on_error)
        self.assertTrue(static.steps[1].continue_on_error)

    def test_merges_workflow_and_job_environment(self) -> None:
        static = self.jobs()["Static"]
        self.assertEqual(static.env, {"GLOBAL": "workflow", "SCOPE": "job"})
        self.assertEqual(self.jobs()["Unit"].env, {"GLOBAL": "workflow"})

    def test_preserves_multi_line_run_blocks(self) -> None:
        unit = self.jobs()["Unit"]
        self.assertEqual(unit.steps[0].run.strip().splitlines(), ["echo first", "make test-unit"])

    def test_records_needs(self) -> None:
        self.assertEqual(self.jobs()["Report"].needs, ["Static", "Unit"])

    def test_notes_a_matrix_it_cannot_expand(self) -> None:
        workflow = write_workflow(
            self.root,
            textwrap.dedent(
                """
                jobs:
                  Matrixed:
                    strategy:
                      matrix:
                        go: ['1.25', '1.26']
                    steps:
                    - run: make test
                """
            ).lstrip(),
            name="matrix.yaml",
        )
        job = ci.parse_workflow(workflow)[0]
        self.assertTrue(any("matrix" in note for note in job.notes))

    def test_rejects_unsupported_shell(self) -> None:
        workflow = write_workflow(
            self.root,
            textwrap.dedent(
                """
                jobs:
                  Pythonic:
                    steps:
                    - name: Script
                      shell: python
                      run: print("hi")
                """
            ).lstrip(),
            name="python.yaml",
        )
        with self.assertRaises(ci.Error) as caught:
            ci.parse_workflow(workflow)
        self.assertIn("shell", str(caught.exception))

    def test_rejects_job_id_that_is_unsafe_as_a_path(self) -> None:
        workflow = write_workflow(
            self.root,
            textwrap.dedent(
                """
                jobs:
                  "../escape":
                    steps:
                    - run: make test
                """
            ).lstrip(),
            name="unsafe.yaml",
        )
        with self.assertRaises(ci.Error):
            ci.parse_workflow(workflow)

    def test_discovers_the_default_workflow(self) -> None:
        found = ci.discover_workflow(self.root, None)
        self.assertEqual(found, self.workflow)

    def test_reports_candidates_when_it_cannot_guess(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        write_workflow(root, WORKFLOW, name="release.yaml")
        with self.assertRaises(ci.Error) as caught:
            ci.discover_workflow(root, None)
        self.assertIn("release.yaml", str(caught.exception))


class JobOrderingTest(unittest.TestCase):
    def make(self, key, needs):
        return ci.Job(
            key=key,
            name=key,
            timeout_minutes=None,
            needs=needs,
            steps=[],
            env={},
            working_directory=None,
            continue_on_error=False,
            skipped_uses=[],
            notes=[],
        )

    def test_groups_independent_jobs_into_one_wave(self) -> None:
        waves = ci.order_jobs([self.make("A", []), self.make("B", [])])
        self.assertEqual([[job.key for job in wave] for wave in waves], [["A", "B"]])

    def test_orders_dependants_into_later_waves(self) -> None:
        jobs = [self.make("C", ["A", "B"]), self.make("A", []), self.make("B", [])]
        waves = ci.order_jobs(jobs)
        self.assertEqual([[job.key for job in wave] for wave in waves], [["A", "B"], ["C"]])

    def test_ignores_needs_on_unselected_jobs(self) -> None:
        waves = ci.order_jobs([self.make("C", ["A"])])
        self.assertEqual([[job.key for job in wave] for wave in waves], [["C"]])

    def test_rejects_a_cycle(self) -> None:
        with self.assertRaises(ci.Error):
            ci.order_jobs([self.make("A", ["B"]), self.make("B", ["A"])])


class HostConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.config = Path(self.temporary.name) / "ci-remote"
        self.config.mkdir(parents=True)
        os.environ["XDG_CONFIG_HOME"] = self.temporary.name
        self.addCleanup(os.environ.pop, "XDG_CONFIG_HOME", None)
        os.environ.pop("CI_REMOTE_HOST", None)

    def write(self, body: str, name: str = "hosts.conf") -> None:
        (self.config / name).write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")

    def test_reads_hosts_and_default(self) -> None:
        self.write(
            """
            [defaults]
            host = big

            [big]
            ssh = big.example
            prelude = export PATH=/opt/go/bin:$PATH
            parallel = 9
            env = GOFLAGS=-count=1 CGO_ENABLED=0
            """
        )
        hosts, default_host = ci.load_hosts()
        self.assertEqual(default_host, "big")
        self.assertEqual(hosts["big"].ssh_target, "big.example")
        self.assertEqual(hosts["big"].parallel, 9)
        self.assertEqual(hosts["big"].env, {"GOFLAGS": "-count=1", "CGO_ENABLED": "0"})

    def test_local_override_wins(self) -> None:
        self.write("[big]\nssh = shared.example\nparallel = 2\n")
        self.write("[big]\nssh = private.example\n", name="hosts.local.conf")
        hosts, _ = ci.load_hosts()
        self.assertEqual(hosts["big"].ssh_target, "private.example")
        self.assertEqual(hosts["big"].parallel, 2)

    def test_ssh_target_defaults_to_section_name(self) -> None:
        self.write("[plain]\nparallel = 1\n")
        hosts, _ = ci.load_hosts()
        self.assertEqual(hosts["plain"].ssh_target, "plain")

    def test_unknown_host_lists_the_known_ones(self) -> None:
        self.write("[a]\n\n[b]\n")
        with self.assertRaises(ci.Error) as caught:
            ci.resolve_host("c")
        self.assertIn("a, b", str(caught.exception))

    def test_missing_configuration_is_a_clear_error(self) -> None:
        with self.assertRaises(ci.Error) as caught:
            ci.load_hosts()
        self.assertIn("no host configuration", str(caught.exception))


class ScriptRenderingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.jobs = {job.key: job for job in ci.parse_workflow(write_workflow(self.root))}
        self.host = ci.Host(
            name="box",
            ssh="box",
            prelude="export PATH=/opt/go/bin:$PATH",
            nice="nice -n 19",
            env={"HOSTVAR": "1"},
        )

    def driver(self, key: str) -> str:
        return ci.render_job_driver(self.host, self.jobs[key], "/r/runs/1", "/r/ws")

    def test_emits_prelude_and_environment(self) -> None:
        driver = self.driver("Static")
        self.assertIn("export PATH=/opt/go/bin:$PATH", driver)
        self.assertIn("export CI=true", driver)
        self.assertIn("export HOSTVAR=1", driver)
        self.assertIn("export SCOPE=job", driver)
        self.assertIn("export GLOBAL=workflow", driver)

    def test_runs_each_step_with_github_bash_semantics(self) -> None:
        driver = self.driver("Static")
        self.assertIn("bash --noprofile --norc -eo pipefail /r/runs/1/Static/step-01.sh", driver)
        # nice wraps the timeout budget, which wraps bash.
        self.assertRegex(driver, r"nice -n 19 .*timeout --kill-after.*bash --noprofile")

    def test_blocking_step_failure_stops_the_job(self) -> None:
        driver = self.driver("Static")
        blocking = driver.split("step-01.sh")[1].split("step-02.sh")[0]
        self.assertIn("overall=$rc", blocking)
        self.assertIn("finish", blocking)

    def test_advisory_step_failure_does_not_stop_the_job(self) -> None:
        driver = self.driver("Static")
        advisory = driver.split("step-02.sh")[1]
        self.assertIn("continue-on-error", advisory)
        self.assertNotIn("overall=$rc", advisory)

    def test_records_a_result_line_with_timings(self) -> None:
        self.assertIn('> "$RUN_DIR/Static.rc"', self.driver("Static"))
        self.assertIn('Static.started', self.driver("Static"))

    def test_dispatch_emits_one_wave_per_dependency_level(self) -> None:
        waves = ci.order_jobs(list(self.jobs.values()))
        dispatch = ci.render_dispatch("/r/runs/1", waves, parallel=4)
        self.assertIn("# wave 1", dispatch)
        self.assertIn("# wave 2", dispatch)
        self.assertLess(dispatch.index("Static Unit"), dispatch.index("Report"))
        self.assertIn("-P 4", dispatch)

    def test_generated_scripts_are_valid_shell(self) -> None:
        for key in self.jobs:
            driver = ci.render_job_driver(self.host, self.jobs[key], "/r/runs/1", "/r/ws")
            result = subprocess.run(["bash", "-n"], input=driver, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, f"{key}: {result.stderr}")
        waves = ci.order_jobs(list(self.jobs.values()))
        dispatch = ci.render_dispatch("/r/runs/1", waves, parallel=4)
        result = subprocess.run(["bash", "-n"], input=dispatch, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class DriverExecutionTest(unittest.TestCase):
    """Run a generated driver for real, with a local directory as the workspace."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run_dir = self.root / "run"
        self.workspace = self.root / "ws"
        (self.run_dir / "J").mkdir(parents=True)
        self.workspace.mkdir()

    def execute(self, body: str, advisory: bool = False, second: str = "echo second") -> tuple[int, str]:
        lines = ["jobs:", "  J:", "    steps:", "    - name: One"]
        if advisory:
            lines.append("      continue-on-error: true")
        lines += [
            f"      run: {body}",
            "    - name: Two",
            f"      run: {second}",
        ]
        workflow = write_workflow(self.root, "\n".join(lines) + "\n", name="exec.yaml")
        job = ci.parse_workflow(workflow)[0]
        host = ci.Host(name="local", ssh="local")
        driver = ci.render_job_driver(host, job, str(self.run_dir), str(self.workspace))
        (self.run_dir / "J" / "run.sh").write_text(driver, encoding="utf-8")
        for step in job.steps:
            (self.run_dir / "J" / f"step-{step.index:02d}.sh").write_text(
                step.run + "\n", encoding="utf-8"
            )
        result = subprocess.run(
            ["bash", str(self.run_dir / "J" / "run.sh")], capture_output=True, text=True
        )
        return result.returncode, result.stdout

    def rc_file(self) -> list[str]:
        return (self.run_dir / "J.rc").read_text(encoding="utf-8").split()

    def test_successful_job_records_zero(self) -> None:
        code, output = self.execute("echo first")
        self.assertEqual(code, 0)
        self.assertIn("first", output)
        self.assertIn("second", output)
        self.assertEqual(self.rc_file()[0], "0")

    def test_failing_step_stops_the_job_and_records_its_code(self) -> None:
        code, output = self.execute("exit 3")
        self.assertEqual(code, 3)
        self.assertNotIn("second", output)
        self.assertEqual(self.rc_file()[0], "3")

    def test_advisory_step_failure_lets_the_job_pass(self) -> None:
        code, output = self.execute("exit 3", advisory=True)
        self.assertEqual(code, 0)
        self.assertIn("second", output)
        self.assertEqual(self.rc_file()[0], "0")

    def test_rc_file_carries_start_and_end_stamps(self) -> None:
        self.execute("echo first")
        fields = self.rc_file()
        self.assertEqual(len(fields), 3)
        self.assertLessEqual(int(fields[1]), int(fields[2]))

    def test_step_runs_inside_an_isolated_copy_not_the_workspace(self) -> None:
        (self.workspace / "marker.txt").write_text("original\n", encoding="utf-8")
        code, output = self.execute("pwd", second="echo done")
        self.assertEqual(code, 0)
        # Each job gets its own tree, so concurrent jobs cannot corrupt one
        # another's checkout the way a shared workspace allows.
        self.assertIn("tree", output)
        self.assertNotIn(f"{self.workspace}\n", output)

    def test_a_job_mutating_its_tree_cannot_affect_the_workspace(self) -> None:
        (self.workspace / "generated.yaml").write_text("before\n", encoding="utf-8")
        code, _ = self.execute(
            "rm -f generated.yaml && echo after > generated.yaml", second="echo done"
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            (self.workspace / "generated.yaml").read_text(encoding="utf-8"),
            "before\n",
            "the shared workspace must be untouched by a job's writes",
        )

    def test_isolated_tree_is_removed_when_the_job_ends(self) -> None:
        self.execute("echo hi", second="echo done")
        self.assertFalse(
            (self.run_dir / "J" / "tree").exists(),
            "job trees must not accumulate; logs are the diagnostic surface",
        )

    def test_isolated_tree_is_removed_after_a_failure_too(self) -> None:
        self.execute("exit 3")
        self.assertFalse((self.run_dir / "J" / "tree").exists())

    def test_pipefail_is_active_for_steps(self) -> None:
        code, _ = self.execute("false | cat", second="echo unreached")
        self.assertEqual(code, 1)

    def test_yaml_coerced_boolean_run_stays_a_command(self) -> None:
        # `run: true` is a YAML boolean; naive str() would emit "True".
        code, _ = self.execute("true", second="echo second")
        self.assertEqual(code, 0)


class StatusParsingTest(unittest.TestCase):
    """fetch_status shells out; stub ssh so the parser is what is under test."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{os.environ['PATH']}"
        self.original_path = os.environ["PATH"]
        self.addCleanup(self.restore_path)

    def restore_path(self) -> None:
        os.environ["PATH"] = self.original_path.split(os.pathsep, 1)[1]

    def stub_ssh(self, payload: str) -> None:
        script = self.bin / "ssh"
        script.write_text(
            "#!/bin/sh\ncat <<'EOF'\n" + payload + "\nEOF\n", encoding="utf-8"
        )
        script.chmod(0o755)

    def test_a_job_waiting_on_admission_reports_queue_not_run(self) -> None:
        # The probe must actually emit Q lines; a job blocked on a lock
        # otherwise reads as RUN and its wait is mistaken for work.
        self.stub_ssh("N 1000\nQ Envtest 900\nQ Race 900\nS Race 950")
        state = ci.fetch_status(ci.Host(name="h", ssh="h"), "/r")
        manifest = {"jobs": ["Envtest", "Race"], "advisory": []}
        self.assertEqual(ci.job_state(manifest, state, "Envtest"), ("QUEUE", "1m40s"))
        # Race was admitted, so it times from its start, not from queueing.
        self.assertEqual(ci.job_state(manifest, state, "Race"), ("RUN", "50s"))

    def test_parses_running_and_finished_jobs(self) -> None:
        self.stub_ssh("N 1000\nS Unit 900\nS Race 950\nR Unit 0 900 940")
        state = ci.fetch_status(ci.Host(name="h", ssh="h"), "/r")
        self.assertEqual(state["now"], 1000)
        self.assertEqual(state["results"]["Unit"], {"rc": 0, "start": 900, "end": 940})
        self.assertIsNone(state["finished"])

        manifest = {"jobs": ["Unit", "Race", "Build"], "advisory": []}
        self.assertEqual(ci.job_state(manifest, state, "Unit"), ("PASS", "40s"))
        self.assertEqual(ci.job_state(manifest, state, "Race"), ("RUN", "50s"))
        self.assertEqual(ci.job_state(manifest, state, "Build"), ("PEND", "-"))

    def test_marks_advisory_job_failures(self) -> None:
        self.stub_ssh("N 100\nS Fmt 10\nR Fmt 1 10 70\nF 70")
        state = ci.fetch_status(ci.Host(name="h", ssh="h"), "/r")
        self.assertEqual(state["finished"], 70)
        strict = {"jobs": ["Fmt"], "advisory": []}
        soft = {"jobs": ["Fmt"], "advisory": ["Fmt"]}
        self.assertEqual(ci.job_state(strict, state, "Fmt"), ("FAIL", "1m00s"))
        self.assertEqual(ci.job_state(soft, state, "Fmt")[0], "FAIL(advisory)")


class GitIgnoreTest(unittest.TestCase):
    """The exclude list must match git's view, negations included."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "-q")

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True
        )

    def touch(self, relative: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")

    def test_respects_a_reinclusion_negation(self) -> None:
        # The shape that broke a real run: ignore a directory, re-include part
        # of it, and track files under the re-included part.
        (self.root / ".gitignore").write_text(
            "/.claude/*\n!/.claude/skills/\nbuild/\n", encoding="utf-8"
        )
        self.touch(".claude/settings.json")
        self.touch(".claude/skills/dev/SKILL.md")
        self.touch("build/artifact.o")
        self.touch("src/main.go")

        ignored = ci.git_ignored_paths(self.root)
        self.assertIn(".claude/settings.json", ignored)
        self.assertIn("build/", ignored)
        # The re-included, tracked path must NOT be excluded from the sync.
        self.assertNotIn(".claude/skills/", ignored)
        self.assertNotIn(".claude/skills/dev/SKILL.md", ignored)
        self.assertNotIn("src/main.go", ignored)

    def test_collapses_a_wholly_ignored_directory(self) -> None:
        (self.root / ".gitignore").write_text("vendor/\n", encoding="utf-8")
        self.touch("vendor/a/one.go")
        self.touch("vendor/b/two.go")
        self.assertEqual(ci.git_ignored_paths(self.root), ["vendor/"])

    def test_reports_a_git_failure(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ci.Error):
            ci.git_ignored_paths(Path(temporary.name) / "not-a-repo")


class LaunchTest(unittest.TestCase):
    def test_orphans_the_dispatcher_and_exits(self) -> None:
        launch = ci.render_launch("/r/runs/1")
        # The subshell is what lets ssh return; without it --detach blocks for
        # the whole run.
        self.assertIn("( setsid bash /r/runs/1/dispatch.sh", launch)
        self.assertIn("& )", launch)
        self.assertIn("< /dev/null", launch)
        self.assertTrue(launch.rstrip().endswith("exit 0"))
        self.assertEqual(
            subprocess.run(["bash", "-n"], input=launch, text=True).returncode, 0
        )

    def test_detaches_for_real(self) -> None:
        """Run the launch shape locally: the shell must exit while work runs."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "dispatch.sh").write_text(
            f"sleep 5\ntouch {root}/done\n", encoding="utf-8"
        )
        # bash -s, exactly as ssh_run invokes it remotely.
        result = subprocess.run(
            ["bash", "-s"],
            input=ci.render_launch(str(root)),
            text=True,
            capture_output=True,
            timeout=3,  # must return long before the 5s dispatcher finishes
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse((root / "done").exists(), "dispatcher should still run")


class PruneTest(unittest.TestCase):
    """Retention runs for real against a local tree standing in for the box."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "runs").mkdir()
        (self.root / "workspaces").mkdir()

    def make_run(self, name: str, finished: bool, age_days: int = 0) -> Path:
        path = self.root / "runs" / name
        path.mkdir()
        (path / "Unit.log").write_text("x\n", encoding="utf-8")
        if finished:
            (path / "finished").write_text("1\n", encoding="utf-8")
        if age_days:
            stamp = time.time() - age_days * 86400
            os.utime(path, (stamp, stamp))
        return path

    def make_workspace(self, name: str, stamp_age_days: int | None) -> Path:
        path = self.root / "workspaces" / name
        path.mkdir()
        (path / "file.txt").write_text("x\n", encoding="utf-8")
        if stamp_age_days is not None:
            stamp = path / ci.WORKSPACE_STAMP
            stamp.write_text("", encoding="utf-8")
            when = time.time() - stamp_age_days * 86400
            os.utime(stamp, (when, when))
        return path

    def prune(self, keep: int = 2, ttl: int = 14) -> str:
        script = ci.render_prune(str(self.root), keep, ttl)
        result = subprocess.run(
            ["bash", "-s"], input=script, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_keeps_the_newest_runs_and_drops_the_rest(self) -> None:
        old = self.make_run("r1", finished=True, age_days=9)
        mid = self.make_run("r2", finished=True, age_days=6)
        new = self.make_run("r3", finished=True, age_days=1)
        newest = self.make_run("r4", finished=True, age_days=0)
        output = self.prune(keep=2)
        self.assertFalse(old.exists())
        self.assertFalse(mid.exists())
        self.assertTrue(new.exists())
        self.assertTrue(newest.exists())
        self.assertIn("pruned run r1", output)

    def test_never_removes_an_unfinished_run(self) -> None:
        running = self.make_run("r1", finished=False, age_days=30)
        for index in range(2, 6):
            self.make_run(f"r{index}", finished=True, age_days=0)
        self.prune(keep=1)
        self.assertTrue(running.exists(), "an in-flight run must survive")

    def test_drops_workspaces_unused_past_the_ttl(self) -> None:
        stale = self.make_workspace("repo-aaaa", stamp_age_days=30)
        fresh = self.make_workspace("repo-bbbb", stamp_age_days=1)
        output = self.prune(ttl=14)
        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())
        self.assertIn("pruned workspace repo-aaaa", output)

    def test_keeps_an_unstamped_workspace(self) -> None:
        # No stamp means unknown age; deleting it would be a guess.
        unstamped = self.make_workspace("repo-cccc", stamp_age_days=None)
        self.prune(ttl=1)
        self.assertTrue(unstamped.exists())

    def test_zero_disables_each_policy(self) -> None:
        run = self.make_run("r1", finished=True, age_days=99)
        workspace = self.make_workspace("repo-aaaa", stamp_age_days=99)
        script = ci.render_prune(str(self.root), 0, 0)
        subprocess.run(["bash", "-s"], input=script, text=True, capture_output=True)
        self.assertTrue(run.exists())
        self.assertTrue(workspace.exists())

    def test_survives_a_missing_root(self) -> None:
        script = ci.render_prune(str(self.root / "absent"), 2, 14)
        result = subprocess.run(
            ["bash", "-s"], input=script, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class AdmissionControlTest(unittest.TestCase):
    """Host-wide limits, which `parallel` alone cannot provide."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.jobs = {
            job.key: job for job in ci.parse_workflow(write_workflow(self.root))
        }

    def driver(self, key: str, **host_kwargs) -> str:
        host = ci.Host(name="box", ssh="box", **host_kwargs)
        return ci.render_job_driver(host, self.jobs[key], "/r/runs/1", "/r/ws")

    def test_locks_live_beside_runs_so_every_run_shares_them(self) -> None:
        # A per-run lock directory would defeat the point: the limit has to
        # bind across invocations from different checkouts.
        self.assertEqual(ci.remote_root_of("/srv/ci/runs/20260101T000000-ab"), "/srv/ci")
        driver = self.driver("Static", max_jobs=4)
        self.assertIn("/r/locks/slot.", driver)
        self.assertNotIn("/r/runs/1/locks", driver)

    def test_takes_one_of_max_jobs_slots(self) -> None:
        driver = self.driver("Static", max_jobs=4)
        self.assertIn("seq 1 4", driver)
        self.assertIn("flock -n", driver)

    def test_no_admission_control_when_unset(self) -> None:
        driver = self.driver("Static")
        self.assertNotIn("slot.", driver)
        self.assertNotIn("exclusive", driver)

    def test_exclusive_job_takes_a_blocking_named_lock(self) -> None:
        driver = self.driver("Static", exclusive_jobs=["Static"])
        self.assertIn("/r/locks/exclusive", driver)
        # Blocking, not -n: it must wait rather than fail.
        self.assertIn('flock "$excl_fd"', driver)

    def test_non_exclusive_job_is_unaffected(self) -> None:
        driver = self.driver("Unit", exclusive_jobs=["Static"])
        self.assertNotIn("exclusive", driver)

    def test_slot_is_released_by_process_exit(self) -> None:
        # Held via an open fd, so a killed job cannot leave a stale lock.
        driver = self.driver("Static", max_jobs=2)
        self.assertRegex(driver, r"exec \{slot_fd\}>")
        self.assertNotIn("rm -f /r/locks", driver)

    def test_admission_runs_before_the_expensive_tree_copy(self) -> None:
        driver = self.driver("Static", max_jobs=2, isolate_jobs=True)
        self.assertLess(driver.index("flock -n"), driver.index("cp -a"))


class TimeoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        body = textwrap.dedent(
            """
            jobs:
              Quick:
                timeout-minutes: 7
                steps:
                - run: make test
              Unbounded:
                steps:
                - run: make test
            """
        ).lstrip()
        self.jobs = {
            job.key: job
            for job in ci.parse_workflow(write_workflow(self.root, body, "t.yaml"))
        }

    def test_reads_timeout_minutes_from_the_workflow(self) -> None:
        self.assertEqual(self.jobs["Quick"].timeout_minutes, 7)
        self.assertIsNone(self.jobs["Unbounded"].timeout_minutes)

    def test_applies_the_job_budget_in_seconds(self) -> None:
        host = ci.Host(name="b", ssh="b")
        driver = ci.render_job_driver(host, self.jobs["Quick"], "/r/runs/1", "/r/ws")
        self.assertIn("JOB_TIMEOUT=420", driver)
        self.assertIn("timeout --kill-after=30s", driver)

    def test_falls_back_to_the_host_default(self) -> None:
        host = ci.Host(name="b", ssh="b", default_timeout_minutes=5)
        driver = ci.render_job_driver(host, self.jobs["Unbounded"], "/r/runs/1", "/r/ws")
        self.assertIn("JOB_TIMEOUT=300", driver)

    def test_a_step_gets_only_the_time_left_in_the_job(self) -> None:
        host = ci.Host(name="b", ssh="b")
        driver = ci.render_job_driver(host, self.jobs["Quick"], "/r/runs/1", "/r/ws")
        # Budget is computed per step from elapsed job time, not restarted.
        self.assertIn("JOB_TIMEOUT - ($(date +%s) - JOB_START)", driver)


class ScratchResolutionTest(unittest.TestCase):
    """Where scratch really lands, not where `env` claims."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.bin = Path(self.temporary.name) / "bin"
        self.bin.mkdir()
        # A stub ssh that runs the probe locally, so what is under test is the
        # shell layering the real host would apply.
        script = self.bin / "ssh"
        script.write_text("#!/bin/sh\nexec bash\n", encoding="utf-8")
        script.chmod(0o755)
        self.original_path = os.environ["PATH"]
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.original_path}"
        self.addCleanup(lambda: os.environ.__setitem__("PATH", self.original_path))

    def test_prelude_wins_over_env(self) -> None:
        # The regression: a prelude redirecting TMPDIR was ignored, so the
        # check measured a /tmp the host never writes to.
        host = ci.Host(
            name="h",
            ssh="h",
            env={"TMPDIR": "/declared"},
            prelude='export TMPDIR="$JOB_DIR/tmp"',
        )
        self.assertEqual(ci.effective_scratch(host, "/srv/ci"), "/srv/ci/.preflight/tmp")

    def test_env_is_used_when_the_prelude_sets_nothing(self) -> None:
        host = ci.Host(name="h", ssh="h", env={"TMPDIR": "/declared"})
        self.assertEqual(ci.effective_scratch(host, "/srv/ci"), "/declared")

    def test_falls_back_to_tmp_when_nothing_configures_it(self) -> None:
        host = ci.Host(name="h", ssh="h")
        self.assertEqual(ci.effective_scratch(host, "/srv/ci"), "/tmp")


class VerdictTest(unittest.TestCase):
    """A run in flight must never be summarised as a pass."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.bin = Path(self.temporary.name) / "bin"
        self.bin.mkdir()
        self.original_path = os.environ["PATH"]
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.original_path}"
        self.addCleanup(lambda: os.environ.__setitem__("PATH", self.original_path))

    def stub_ssh(self, payload: str) -> None:
        script = self.bin / "ssh"
        script.write_text(
            "#!/bin/sh\ncat <<'EOF'\n" + payload + "\nEOF\n", encoding="utf-8"
        )
        script.chmod(0o755)

    def summarise(self, payload: str) -> tuple[int, str]:
        self.stub_ssh(payload)
        manifest = {
            "run_id": "r1",
            "host": "h",
            "repo": "/repo",
            "revision": "abc",
            "run_dir": "/r",
            "jobs": ["Unit", "Race"],
            "advisory": [],
        }
        import io
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = ci.summarise(ci.Host(name="h", ssh="h"), manifest, tail=0)
        return code, buffer.getvalue()

    def test_mid_run_is_not_reported_as_success(self) -> None:
        # Unit passed, Race still going: the old code said "all jobs passed".
        code, output = self.summarise("N 100\nS Unit 10\nR Unit 0 10 40\nS Race 20")
        self.assertEqual(code, 3)
        self.assertIn("NOT FINISHED", output)
        self.assertNotIn("all jobs passed", output)
        self.assertIn("Race", output)

    def test_completed_and_green_is_a_pass(self) -> None:
        code, output = self.summarise(
            "N 100\nS Unit 10\nR Unit 0 10 40\nS Race 10\nR Race 0 10 50\nF 50"
        )
        self.assertEqual(code, 0)
        self.assertIn("all jobs passed", output)

    def test_a_failure_outranks_an_unfinished_job(self) -> None:
        code, output = self.summarise("N 100\nS Unit 10\nR Unit 1 10 40\nS Race 20")
        self.assertEqual(code, 1)
        self.assertIn("failed", output)


class OverrideFlagTest(unittest.TestCase):
    """Low-disk and workspace-seizure overrides must stay separate."""

    def parse(self, *argv: str):
        return ci.build_parser().parse_args(["run", *argv])

    def test_force_does_not_imply_taking_a_live_workspace(self) -> None:
        args = self.parse("--force")
        self.assertTrue(args.force)
        self.assertFalse(args.take_workspace)

    def test_take_workspace_does_not_imply_ignoring_disk(self) -> None:
        args = self.parse("--take-workspace")
        self.assertTrue(args.take_workspace)
        self.assertFalse(args.force)


class WorkspaceKeyTest(unittest.TestCase):
    def test_is_stable_and_distinguishes_worktrees(self) -> None:
        first = ci.workspace_key(Path("/home/a/Projects/repo"))
        again = ci.workspace_key(Path("/home/a/Projects/repo"))
        other = ci.workspace_key(Path("/home/a/worktrees/repo"))
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("repo-"))


class UploadTest(unittest.TestCase):
    """upload_tree writes remote files through a single ssh heredoc stream."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # A stub ssh that executes the payload locally is the closest honest
        # analogue of the remote shell: it proves the generated stream is valid.
        # ci-remote feeds the script on stdin (see ssh_run), so exec a shell.
        script = self.bin / "ssh"
        script.write_text("#!/bin/sh\nexec bash\n", encoding="utf-8")
        script.chmod(0o755)
        self.original_path = os.environ["PATH"]
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.original_path}"
        self.addCleanup(lambda: os.environ.__setitem__("PATH", self.original_path))

    def test_writes_every_file_and_marks_it_executable(self) -> None:
        target = self.root / "remote" / "runs" / "1"
        files = {
            f"{target}/J/run.sh": "#!/bin/sh\necho hello\n",
            f"{target}/J/step-01.sh": "make lint\n",
            f"{target}/dispatch.sh": "#!/bin/sh\ntrue\n",
        }
        ci.upload_tree(ci.Host(name="h", ssh="h"), files)
        for path, content in files.items():
            written = Path(path)
            self.assertTrue(written.exists(), path)
            self.assertEqual(written.read_text(encoding="utf-8"), content)
            self.assertTrue(os.access(written, os.X_OK), path)

    def test_preserves_shell_metacharacters_in_step_bodies(self) -> None:
        target = self.root / "remote"
        body = "make test-integration COMPONENT=restore-courier FOCUS='a b' $HOME `id` \"q\"\n"
        ci.upload_tree(ci.Host(name="h", ssh="h"), {f"{target}/step-01.sh": body})
        self.assertEqual(
            Path(f"{target}/step-01.sh").read_text(encoding="utf-8"), body
        )


class ManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        os.environ["XDG_STATE_HOME"] = self.temporary.name
        self.addCleanup(os.environ.pop, "XDG_STATE_HOME", None)

    def test_round_trips_and_remembers_the_last_run(self) -> None:
        manifest = {"run_id": "20260804T090000-ab12", "host": "big", "jobs": ["Unit"]}
        ci.save_manifest(manifest)
        self.assertEqual(ci.load_manifest("20260804T090000-ab12"), manifest)
        self.assertEqual(ci.load_manifest(None), manifest)

    def test_unknown_run_is_a_clear_error(self) -> None:
        with self.assertRaises(ci.Error) as caught:
            ci.load_manifest("nope")
        self.assertIn("unknown run", str(caught.exception))


class DurationTest(unittest.TestCase):
    def test_formats_seconds_and_minutes(self) -> None:
        self.assertEqual(ci.duration(0), "0s")
        self.assertEqual(ci.duration(59), "59s")
        self.assertEqual(ci.duration(60), "1m00s")
        self.assertEqual(ci.duration(605), "10m05s")
        self.assertEqual(ci.duration(None), "-")


if __name__ == "__main__":
    unittest.main()
