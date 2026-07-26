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
                "--scope",
                "--quiet",
                "--collect",
                "--same-dir",
                "--slice=nks-agent-tests.slice",
                "--",
            ],
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

    def test_heavy_lock_is_held_while_scope_runs(self) -> None:
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

    def test_heavy_lock_is_not_inherited_when_scope_launcher_crashes(self) -> None:
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

    def test_heavy_propagates_scope_command_exit_status(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
