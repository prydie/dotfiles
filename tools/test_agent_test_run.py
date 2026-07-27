from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "agent-test-run"
DISPATCH = (
    Path(__file__).parents[1]
    / "libexec"
    / "agent-test-shims"
    / "agent-test-dispatch"
)
ENV_EXEC = Path(__file__).parents[1] / "libexec" / "agent-test-env-exec"


class AgentTestRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "systemd-run-arguments"
        self.exec_capture = self.root / "systemd-run-command"
        self.write_executable(
            "systemctl",
            """
            #!/bin/sh
            case "$*" in
                *CPUQuotaPerSecUSec*) printf '%s\\n' "${FAKE_QUOTA:-2s}" ;;
                *MemoryMax*) printf '%s\\n' "${FAKE_MEMORY_MAX:-17179869184}" ;;
                *ActiveState*)
                    if [ -n "${CHILD_PID:-}" ] &&
                        [ -s "$CHILD_PID" ] &&
                        kill -0 "$(cat "$CHILD_PID")" 2>/dev/null; then
                        printf 'active\\n'
                    else
                        printf 'inactive\\n'
                    fi
                    ;;
                *) exit 2 ;;
            esac
            """,
        )
        self.write_executable(
            "systemd-run",
            """
            #!/bin/sh
            : > "$CAPTURE"
            if [ -n "${LAUNCHER_PID:-}" ]; then
                printf '%s\\n' "$$" > "$LAUNCHER_PID"
            fi
            sleep "${FAKE_SYSTEMD_RUN_START_DELAY:-0}"
            while [ "$#" -gt 0 ]; do
                printf '%s\\n' "$1" >> "$CAPTURE"
                if [ "$1" = "--" ]; then
                    shift
                    printf '%s\\n' "$@" > "$EXEC_CAPTURE"
                    if [ "${FAKE_SYSTEMD_RUN_CRASH:-}" = 1 ]; then
                        "$@" </dev/null >/dev/null 2>&1 &
                        printf '%s\\n' "$!" > "$CHILD_PID"
                        kill -KILL "$$"
                    fi
                    exec "$@"
                fi
                shift
            done
            exit 2
            """,
        )
        self.write_executable(
            "nice",
            """
            #!/bin/sh
            shift 2
            exec "$@"
            """,
        )
        self.write_executable(
            "ionice",
            """
            #!/bin/sh
            shift 2
            exec "$@"
            """,
        )
        self.write_executable(
            "probe",
            """
            #!/bin/sh
            printf 'argument=%s\\n' "$1"
            printf 'gomaxprocs=%s\\n' "$GOMAXPROCS"
            printf 'goflags=%s\\n' "$GOFLAGS"
            """,
        )
        self.write_executable(
            "go",
            """
            #!/bin/sh
            sleep "${FAKE_GO_SLEEP:-0}"
            """,
        )
        self.write_executable(
            "make",
            """
            #!/bin/sh
            sleep "${FAKE_MAKE_SLEEP:-0}"
            """,
        )
        self.write_executable(
            "ginkgo",
            """
            #!/bin/sh
            sleep "${FAKE_GINKGO_SLEEP:-0}"
            """,
        )
        self.write_executable(
            "tlc",
            """
            #!/bin/sh
            exit 99
            """,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_executable(self, name: str, source: str) -> None:
        path = self.bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def environment(self) -> dict[str, str]:
        return {
            **os.environ,
            "CAPTURE": str(self.capture),
            "EXEC_CAPTURE": str(self.exec_capture),
            "NKS_AGENT_TEST_ENV_EXEC": str(ENV_EXEC),
            "PATH": f"{self.bin}:/usr/bin:/bin",
        }

    def isolated_script(self, lock: Path) -> Path:
        script = self.root / "agent-test-run"
        source = SCRIPT.read_text(encoding="utf-8").replace(
            "/tmp/nks-agent-heavy-test.lock",
            str(lock),
        )
        script.write_text(source, encoding="utf-8")
        script.chmod(0o755)
        return script

    def wait_for_path(self, path: Path) -> None:
        for _ in range(100):
            if path.exists():
                return
            time.sleep(0.01)
        self.fail(f"timed out waiting for {path}")

    def assert_command_holds_heavy_lock(
        self,
        command: list[str],
        sleep_variable: str,
        *,
        expected: bool,
        extra_environment: dict[str, str] | None = None,
    ) -> None:
        lock = self.root / "heavy.lock"
        environment = {
            **self.environment(),
            sleep_variable: "30",
            **(extra_environment or {}),
        }
        process = subprocess.Popen(
            [str(self.isolated_script(lock)), *command],
            cwd=self.root,
            env=environment,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            self.wait_for_path(self.capture)
            probe = subprocess.run(
                ["flock", "-n", str(lock), "true"],
                check=False,
                capture_output=True,
                text=True,
            )
            if expected:
                self.assertNotEqual(probe.returncode, 0)
            else:
                self.assertEqual(probe.returncode, 0, probe.stderr)
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)

    def assert_remote_only(
        self,
        command: list[str],
        *,
        extra_environment: dict[str, str] | None = None,
    ) -> None:
        lock = self.root / "heavy.lock"
        result = subprocess.run(
            [str(self.isolated_script(lock)), *command],
            cwd=self.root,
            env={**self.environment(), **(extra_environment or {})},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "run integration, chaos, and TLA+ tests on cloud-dev",
            result.stderr,
        )
        self.assertIn(
            "ssh cloud-dev 'cd <remote-checkout> && <command>'",
            result.stderr,
        )
        self.assertNotIn("flock", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_launches_a_bounded_focused_command(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "probe", "hello world"],
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("argument=hello world", result.stdout)
        self.assertIn("gomaxprocs=2", result.stdout)
        self.assertIn("goflags=-p=2", result.stdout)
        arguments = self.capture.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            [
                argument
                for argument in arguments
                if not argument.startswith(
                    (
                        "--setenv=",
                        "--unit=nks-agent-test-",
                        "--property=BindsTo=",
                        "--property=After=",
                    )
                )
            ],
            [
                "--user",
                "--quiet",
                "--collect",
                "--wait",
                "--pipe",
                "--same-dir",
                "--slice=nks-agent-tests.slice",
                "--service-type=exec",
                "--property=KillMode=control-group",
                "--",
            ],
        )
        command = self.exec_capture.read_text(encoding="utf-8").splitlines()
        self.assertNotIn("hello world", command)

    def test_service_imports_caller_environment_by_name_without_logging_values(
        self,
    ) -> None:
        environment = self.environment()
        environment["KUBEBUILDER_ASSETS"] = "/sensitive/review/envtest-assets"
        environment["NKS_REVIEW_SECRET"] = "do-not-log-this-value"
        environment["NKS_REVIEW_MULTILINE"] = "first\nFAKE_NAME=still-a-value"

        result = subprocess.run(
            [str(SCRIPT), "probe", "environment"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = self.capture.read_text(encoding="utf-8").splitlines()
        self.assertFalse(
            any(argument.startswith("--setenv=") for argument in arguments),
            arguments,
        )
        command = self.exec_capture.read_text(encoding="utf-8").splitlines()
        self.assertIn(str(ENV_EXEC), command)
        captured = "\n".join([*arguments, *command])
        self.assertNotIn(environment["KUBEBUILDER_ASSETS"], captured)
        self.assertNotIn(environment["NKS_REVIEW_SECRET"], captured)

    def test_service_binds_to_the_invoking_systemd_unit(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "probe", "binding"],
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = self.capture.read_text(encoding="utf-8").splitlines()
        self.assertTrue(
            any(argument.startswith("--property=BindsTo=") for argument in arguments),
            arguments,
        )
        self.assertTrue(
            any(argument.startswith("--property=After=") for argument in arguments),
            arguments,
        )

    def test_focused_envtest_remains_parallel(self) -> None:
        self.assert_command_holds_heavy_lock(
            [
                "go",
                "test",
                "-tags=envtest",
                "./internal/controllers/rollout",
            ],
            "FAKE_GO_SLEEP",
            expected=False,
        )

    def test_full_envtest_target_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["make", "test-envtest"], "FAKE_MAKE_SLEEP", expected=True
        )

    def test_postdeploy_suite_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["make", "test-postdeploy"], "FAKE_MAKE_SLEEP", expected=True
        )

    def test_broad_ginkgo_run_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["ginkgo", "./internal/controllers/..."],
            "FAKE_GINKGO_SLEEP",
            expected=True,
        )

    def test_broad_import_path_go_run_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["go", "test", "example.invalid/project/..."],
            "FAKE_GO_SLEEP",
            expected=True,
        )

    def test_multiple_import_path_go_run_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            [
                "go",
                "test",
                "-run",
                "TestFocused",
                "example.invalid/project/one",
                "example.invalid/project/two",
            ],
            "FAKE_GO_SLEEP",
            expected=True,
        )

    def test_local_integration_test_is_rejected_with_remote_guidance(self) -> None:
        self.assert_remote_only(
            [
                "go",
                "test",
                "-tags=integration",
                "./test/integration/cni",
            ]
        )

    def test_local_integration_test_with_split_tags_is_rejected(self) -> None:
        self.assert_remote_only(["go", "test", "-tags", "integration", "."])

    def test_local_ginkgo_integration_test_with_split_tags_is_rejected(self) -> None:
        self.assert_remote_only(["ginkgo", "--tags", "integration", "."])

    def test_local_chaos_make_target_is_rejected(self) -> None:
        self.assert_remote_only(["make", "test-chaos"])

    def test_local_chaos_go_tag_is_rejected(self) -> None:
        self.assert_remote_only(["go", "test", "-tags=chaos", "."])

    def test_local_chaos_package_is_rejected(self) -> None:
        self.assert_remote_only(["go", "test", "./test/chaos/..."])

    def test_effective_integration_goflags_are_rejected(self) -> None:
        self.assert_remote_only(
            ["go", "test", "./internal/controllers/rollout"],
            extra_environment={"GOFLAGS": "-tags=integration"},
        )

    def test_effective_chaos_goflags_are_rejected(self) -> None:
        self.assert_remote_only(
            ["go", "test", "./internal/controllers/rollout"],
            extra_environment={"GOFLAGS": "-tags=unit,chaos"},
        )

    def test_local_tlc_is_rejected_without_starting_it(self) -> None:
        self.assert_remote_only(["tlc", "MC_example.cfg"])

    def test_focused_unit_test_remains_parallel(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["go", "test", "./internal/controllers/rollout"],
            "FAKE_GO_SLEEP",
            expected=False,
        )

    def test_focused_import_path_with_run_filter_remains_parallel(self) -> None:
        self.assert_command_holds_heavy_lock(
            [
                "go",
                "test",
                "-run",
                "TestFocused",
                "example.invalid/project/one",
            ],
            "FAKE_GO_SLEEP",
            expected=False,
        )

    def test_go_generate_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["go", "generate", "./internal/controllers/rollout"],
            "FAKE_GO_SLEEP",
            expected=True,
        )

    def test_ginkgo_race_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["ginkgo", "--race", "./internal/controllers/rollout"],
            "FAKE_GINKGO_SLEEP",
            expected=True,
        )

    def test_effective_goflags_race_is_serialised(self) -> None:
        self.assert_command_holds_heavy_lock(
            ["go", "test", "./internal/controllers/rollout"],
            "FAKE_GO_SLEEP",
            expected=True,
            extra_environment={"GOFLAGS": "-race"},
        )

    def test_refuses_to_run_without_a_memory_limit(self) -> None:
        environment = self.environment()
        environment["FAKE_MEMORY_MAX"] = "infinity"

        result = subprocess.run(
            [str(SCRIPT), "probe", "ignored"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("does not have a finite memory limit", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_heavy_lock_is_held_while_service_runs(self) -> None:
        lock = self.root / "heavy.lock"
        process = subprocess.Popen(
            [str(self.isolated_script(lock)), "--heavy", "sleep", "30"],
            cwd=self.root,
            env=self.environment(),
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            self.wait_for_path(self.capture)
            probe = subprocess.run(
                ["flock", "-n", str(lock), "true"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(probe.returncode, 0)
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)

    def test_heavy_lock_is_not_inherited_when_service_launcher_crashes(self) -> None:
        lock = self.root / "heavy.lock"
        child_pid_file = self.root / "child.pid"
        child_result = self.root / "child-result"
        self.write_executable(
            "lock-probe",
            """
            #!/bin/sh
            result=clean
            for fd in /proc/$$/fd/*; do
                if [ "$(readlink "$fd" 2>/dev/null || true)" = "$EXPECTED_LOCK" ]; then
                    result=inherited
                fi
            done
            printf '%s\\n' "$result" > "$CHILD_RESULT"
            sleep 0.3
            """,
        )
        environment = self.environment()
        environment["FAKE_SYSTEMD_RUN_CRASH"] = "1"
        environment["CHILD_PID"] = str(child_pid_file)
        environment["CHILD_RESULT"] = str(child_result)
        environment["EXPECTED_LOCK"] = str(lock)

        started = time.monotonic()
        result = subprocess.run(
            [str(self.isolated_script(lock)), "--heavy", "lock-probe"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        elapsed = time.monotonic() - started

        self.assertEqual(result.returncode, 137)
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertEqual(child_result.read_text(encoding="utf-8").strip(), "clean")

        probe = subprocess.run(
            ["flock", "-n", str(lock), "true"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)

    def test_cancelling_during_service_creation_stops_the_launcher(self) -> None:
        environment = self.environment()
        environment["FAKE_SYSTEMD_RUN_START_DELAY"] = "30"
        launcher_pid_file = self.root / "launcher.pid"
        environment["LAUNCHER_PID"] = str(launcher_pid_file)
        process = subprocess.Popen(
            [str(SCRIPT), "probe", "creation-race"],
            cwd=self.root,
            env=environment,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            self.wait_for_path(self.capture)
            self.wait_for_path(launcher_pid_file)
            process.terminate()
            self.assertEqual(process.wait(timeout=2), 143)
            launcher_pid = launcher_pid_file.read_text(encoding="utf-8").strip()
            self.assertFalse(Path(f"/proc/{launcher_pid}").exists())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)

    def test_heavy_propagates_service_command_exit_status(self) -> None:
        lock = self.root / "heavy.lock"
        result = subprocess.run(
            [
                str(self.isolated_script(lock)),
                "--heavy",
                "sh",
                "-c",
                "exit 23",
            ],
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 23)
        probe = subprocess.run(
            ["flock", "-n", str(lock), "true"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)


class AgentTestDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "capture"
        self.write_executable(
            "go",
            """
            #!/bin/sh
            printf 'direct-go:%s\\n' "$*"
            """,
        )
        self.write_executable(
            "agent-test-run",
            """
            #!/bin/sh
            printf '%s\\n' "$@" > "$CAPTURE"
            """,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_executable(self, name: str, source: str) -> None:
        path = self.bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def environment(self) -> dict[str, str]:
        return {
            **os.environ,
            "CAPTURE": str(self.capture),
            "NKS_AGENT_TEST_ORIGINAL_PATH": f"{self.bin}:/usr/bin:/bin",
            "PATH": f"{DISPATCH.parent}:{self.bin}:/usr/bin:/bin",
        }

    def test_direct_go_test_is_routed_through_the_test_runner(self) -> None:
        result = subprocess.run(
            [str(DISPATCH), "test", "-tags=envtest", "./internal/controllers"],
            cwd=self.root,
            env={**self.environment(), "NKS_AGENT_TEST_PROGRAM": "go"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.capture.read_text(encoding="utf-8").splitlines(),
            [
                "--nested",
                str(self.bin / "go"),
                "test",
                "-tags=envtest",
                "./internal/controllers",
            ],
        )

    def test_go_generate_is_routed_through_the_test_runner(self) -> None:
        result = subprocess.run(
            [str(DISPATCH), "generate", "./internal/controllers"],
            cwd=self.root,
            env={**self.environment(), "NKS_AGENT_TEST_PROGRAM": "go"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.capture.read_text(encoding="utf-8").splitlines(),
            [
                "--nested",
                str(self.bin / "go"),
                "generate",
                "./internal/controllers",
            ],
        )

    def test_active_marker_cannot_bypass_routing_outside_test_slice(self) -> None:
        result = subprocess.run(
            [str(DISPATCH), "test", "./internal/controllers"],
            cwd=self.root,
            env={
                **self.environment(),
                "NKS_AGENT_TEST_PROGRAM": "go",
                "NKS_AGENT_TEST_RUN_ACTIVE": "1",
            },
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.capture.exists())

    def test_non_test_go_command_runs_without_the_test_runner(self) -> None:
        result = subprocess.run(
            [str(DISPATCH), "env", "GOMOD"],
            cwd=self.root,
            env={**self.environment(), "NKS_AGENT_TEST_PROGRAM": "go"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "direct-go:env GOMOD")
        self.assertFalse(self.capture.exists())

    def test_missing_original_path_does_not_recurse_through_shim(self) -> None:
        environment = self.environment()
        environment.pop("NKS_AGENT_TEST_ORIGINAL_PATH")
        environment["PATH"] = (
            f"{DISPATCH.parent}:{self.bin}:{DISPATCH.parent}:/usr/bin:/bin"
        )

        result = subprocess.run(
            [str(DISPATCH), "env", "GOMOD"],
            cwd=self.root,
            env={**environment, "NKS_AGENT_TEST_PROGRAM": "go"},
            text=True,
            capture_output=True,
            check=False,
            timeout=1,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "direct-go:env GOMOD")
        self.assertFalse(self.capture.exists())


class AgentTestRunSystemdTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not shutil.which("systemctl") or not shutil.which("systemd-run"):
            raise unittest.SkipTest("systemd user tools are unavailable")
        probe = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                "nks-agent-tests.slice",
                "--property=MemoryMax",
                "--value",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if probe.returncode != 0:
            raise unittest.SkipTest("systemd user manager is unavailable")

    def test_real_service_preserves_environment_and_literal_arguments(self) -> None:
        environment = {
            **os.environ,
            "KUBEBUILDER_ASSETS": "/tmp/nks-review-envtest-assets",
            "NKS_SCHEDULER_SENTINEL": "/tmp/nks-review-envtest-assets",
        }
        result = subprocess.run(
            [
                str(SCRIPT),
                "sh",
                "-c",
                '[ "$KUBEBUILDER_ASSETS" = "$NKS_SCHEDULER_SENTINEL" ] && '
                '[ "$$" != "$" ]',
            ],
            cwd=SCRIPT.parents[1],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_nested_test_shim_executes_directly_inside_test_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            result_file = root / "result"
            fake_go = fake_bin / "go"
            fake_go.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$RESULT_FILE\"\n",
                encoding="utf-8",
            )
            fake_go.chmod(0o755)
            environment = {
                **os.environ,
                "PATH": (
                    f"{DISPATCH.parent}:{SCRIPT.parent}:{fake_bin}:/usr/bin:/bin"
                ),
                "NKS_AGENT_TEST_ORIGINAL_PATH": (
                    f"{SCRIPT.parent}:{fake_bin}:/usr/bin:/bin"
                ),
                "NKS_AGENT_TEST_SHIMS_ACTIVE": "1",
                "RESULT_FILE": str(result_file),
            }

            result = subprocess.run(
                [str(SCRIPT), "sh", "-c", "go test ./focused"],
                cwd=SCRIPT.parents[1],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result_file.read_text(encoding="utf-8").strip(),
                "test ./focused",
            )

    def test_nested_integration_test_is_rejected_inside_test_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            result_file = root / "result"
            fake_go = fake_bin / "go"
            fake_go.write_text(
                "#!/bin/sh\nprintf 'unexpected\\n' > \"$RESULT_FILE\"\n",
                encoding="utf-8",
            )
            fake_go.chmod(0o755)
            environment = {
                **os.environ,
                "PATH": (
                    f"{DISPATCH.parent}:{SCRIPT.parent}:{fake_bin}:/usr/bin:/bin"
                ),
                "NKS_AGENT_TEST_ORIGINAL_PATH": (
                    f"{SCRIPT.parent}:{fake_bin}:/usr/bin:/bin"
                ),
                "NKS_AGENT_TEST_SHIMS_ACTIVE": "1",
                "RESULT_FILE": str(result_file),
            }

            result = subprocess.run(
                [
                    str(SCRIPT),
                    "sh",
                    "-c",
                    "go test -tags=integration ./test/integration/cni",
                ],
                cwd=SCRIPT.parents[1],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(
                "run integration, chaos, and TLA+ tests on cloud-dev",
                result.stderr,
            )
            self.assertFalse(result_file.exists())

    def test_nested_broad_test_acquires_heavy_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            lock = root / "heavy.lock"
            result_file = root / "result"
            nested_runner = fake_bin / "agent-test-run"
            nested_runner.write_text(
                SCRIPT.read_text(encoding="utf-8").replace(
                    "/tmp/nks-agent-heavy-test.lock",
                    str(lock),
                ),
                encoding="utf-8",
            )
            nested_runner.chmod(0o755)
            fake_go = fake_bin / "go"
            fake_go.write_text(
                "#!/bin/sh\n"
                "if flock -n \"$EXPECTED_LOCK\" true; then\n"
                "  printf 'free\\n' > \"$RESULT_FILE\"\n"
                "else\n"
                "  printf 'held\\n' > \"$RESULT_FILE\"\n"
                "fi\n",
                encoding="utf-8",
            )
            fake_go.chmod(0o755)
            environment = {
                **os.environ,
                "PATH": f"{DISPATCH.parent}:{fake_bin}:/usr/bin:/bin",
                "NKS_AGENT_TEST_ORIGINAL_PATH": f"{fake_bin}:/usr/bin:/bin",
                "NKS_AGENT_TEST_ENV_EXEC": str(ENV_EXEC),
                "NKS_AGENT_TEST_SHIMS_ACTIVE": "1",
                "EXPECTED_LOCK": str(lock),
                "RESULT_FILE": str(result_file),
            }

            result = subprocess.run(
                [str(nested_runner), "sh", "-c", "go test ./..."],
                cwd=SCRIPT.parents[1],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result_file.read_text(encoding="utf-8").strip(),
                "held",
            )

    def test_cancelling_wrapper_stops_its_transient_service(self) -> None:
        process = subprocess.Popen(
            [str(SCRIPT), "sh", "-c", "sleep 60"],
            cwd=SCRIPT.parents[1],
            env=os.environ.copy(),
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        unit = f"nks-agent-test-{process.pid}.service"
        main_pid = 0
        try:
            for _ in range(100):
                state = subprocess.run(
                    [
                        "systemctl",
                        "--user",
                        "show",
                        unit,
                        "--property=ActiveState",
                        "--value",
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if state.returncode == 0 and state.stdout.strip() == "active":
                    pid_result = subprocess.run(
                        [
                            "systemctl",
                            "--user",
                            "show",
                            unit,
                            "--property=MainPID",
                            "--value",
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    main_pid = int(pid_result.stdout.strip())
                    break
                time.sleep(0.05)
            else:
                self.fail(f"{unit} did not become active")

            process.terminate()
            self.assertEqual(process.wait(timeout=5), 143)

            for _ in range(100):
                state = subprocess.run(
                    [
                        "systemctl",
                        "--user",
                        "show",
                        unit,
                        "--property=ActiveState",
                        "--value",
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if state.returncode != 0 or state.stdout.strip() not in {
                    "active",
                    "activating",
                    "deactivating",
                }:
                    break
                time.sleep(0.05)
            else:
                self.fail(f"{unit} remained active after wrapper cancellation")

            self.assertFalse(Path(f"/proc/{main_pid}").exists())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            subprocess.run(
                ["systemctl", "--user", "stop", unit],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

    def test_cancelling_while_waiting_for_heavy_lock_exits_promptly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "heavy.lock"
            script = root / "agent-test-run"
            script.write_text(
                SCRIPT.read_text(encoding="utf-8").replace(
                    "/tmp/nks-agent-heavy-test.lock",
                    str(lock),
                ),
                encoding="utf-8",
            )
            script.chmod(0o755)
            holder = subprocess.Popen(
                ["flock", str(lock), "sleep", "60"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(100):
                probe = subprocess.run(
                    ["flock", "-n", str(lock), "true"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                if probe.returncode != 0:
                    break
                time.sleep(0.01)
            else:
                self.fail("lock holder did not acquire the heavy lock")
            process = subprocess.Popen(
                [str(script), "--heavy", "true"],
                cwd=SCRIPT.parents[1],
                env={
                    **os.environ,
                    "NKS_AGENT_TEST_ENV_EXEC": str(ENV_EXEC),
                },
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                time.sleep(0.1)
                process.terminate()
                self.assertEqual(process.wait(timeout=2), 143)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                holder.terminate()
                holder.wait(timeout=5)

    def test_stopping_invoking_scope_stops_bound_test_service(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pid_file = root / "wrapper.pid"
            owner_launcher = root / "owner-launcher"
            owner_launcher.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$$\" > \"$1\"\n"
                "exec \"$2\" sh -c 'sleep 60'\n",
                encoding="utf-8",
            )
            owner_launcher.chmod(0o755)
            owner = f"nks-agent-test-owner-{os.getpid()}.scope"
            launcher = subprocess.Popen(
                [
                    "systemd-run",
                    "--user",
                    "--scope",
                    "--quiet",
                    "--collect",
                    f"--unit={owner}",
                    "--same-dir",
                    "--",
                    str(owner_launcher),
                    str(pid_file),
                    str(SCRIPT),
                ],
                cwd=SCRIPT.parents[1],
                env=os.environ.copy(),
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            unit = ""
            try:
                for _ in range(100):
                    if pid_file.exists():
                        unit = (
                            f"nks-agent-test-{pid_file.read_text().strip()}.service"
                        )
                        state = subprocess.run(
                            [
                                "systemctl",
                                "--user",
                                "show",
                                unit,
                                "--property=ActiveState",
                                "--value",
                            ],
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                        if state.returncode == 0 and state.stdout.strip() == "active":
                            break
                    time.sleep(0.05)
                else:
                    self.fail("bound test service did not become active")

                subprocess.run(
                    ["systemctl", "--user", "stop", owner],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                launcher.wait(timeout=5)

                for _ in range(100):
                    state = subprocess.run(
                        [
                            "systemctl",
                            "--user",
                            "show",
                            unit,
                            "--property=ActiveState",
                            "--value",
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    if state.returncode != 0 or state.stdout.strip() not in {
                        "active",
                        "activating",
                        "deactivating",
                    }:
                        break
                    time.sleep(0.05)
                else:
                    self.fail(f"{unit} survived its invoking scope")
            finally:
                subprocess.run(
                    ["systemctl", "--user", "stop", owner],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                if unit:
                    subprocess.run(
                        ["systemctl", "--user", "stop", unit],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                if launcher.poll() is None:
                    os.killpg(launcher.pid, signal.SIGKILL)
                    launcher.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
