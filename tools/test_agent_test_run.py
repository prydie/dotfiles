from __future__ import annotations

import os
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


class AgentTestRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "systemd-run-arguments"
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
            while [ "$#" -gt 0 ]; do
                printf '%s\\n' "$1" >> "$CAPTURE"
                if [ "$1" = "--" ]; then
                    shift
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
        self.assertEqual(
            self.capture.read_text(encoding="utf-8").splitlines(),
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

    def test_focused_envtest_remains_parallel(self) -> None:
        lock = self.root / "heavy.lock"
        environment = self.environment()
        environment["FAKE_GO_SLEEP"] = "30"
        process = subprocess.Popen(
            [
                str(self.isolated_script(lock)),
                "go",
                "test",
                "-tags=envtest",
                "./internal/controllers/rollout",
            ],
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
            self.assertEqual(probe.returncode, 0, probe.stderr)
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)

    def test_full_envtest_target_is_serialised(self) -> None:
        lock = self.root / "heavy.lock"
        environment = self.environment()
        environment["FAKE_MAKE_SLEEP"] = "30"
        process = subprocess.Popen(
            [
                str(self.isolated_script(lock)),
                "make",
                "test-envtest",
            ],
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
            self.assertNotEqual(probe.returncode, 0)
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)

    def test_local_integration_test_is_rejected_with_remote_guidance(self) -> None:
        lock = self.root / "heavy.lock"
        result = subprocess.run(
            [
                str(self.isolated_script(lock)),
                "go",
                "test",
                "-tags=integration",
                "./test/integration/cni",
            ],
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("run integration and TLA+ tests on cloud-dev", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_local_tlc_is_rejected_without_starting_it(self) -> None:
        lock = self.root / "heavy.lock"
        result = subprocess.run(
            [
                str(self.isolated_script(lock)),
                "tlc",
                "MC_example.cfg",
            ],
            cwd=self.root,
            env=self.environment(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("run integration and TLA+ tests on cloud-dev", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_focused_unit_test_remains_parallel(self) -> None:
        lock = self.root / "heavy.lock"
        environment = self.environment()
        environment["FAKE_GO_SLEEP"] = "30"
        process = subprocess.Popen(
            [
                str(self.isolated_script(lock)),
                "go",
                "test",
                "./internal/controllers/rollout",
            ],
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
            self.assertEqual(probe.returncode, 0, probe.stderr)
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)

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
                str(self.bin / "go"),
                "test",
                "-tags=envtest",
                "./internal/controllers",
            ],
        )

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


if __name__ == "__main__":
    unittest.main()
