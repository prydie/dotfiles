from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "agent-run"


class AgentRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "systemd-run-arguments"
        self.reload_stamp = self.root / "daemon-reload-stamp"
        self.write_executable(
            "systemctl",
            """
            #!/bin/sh
            reloaded() {
                [ -e "${RELOAD_STAMP:-/nonexistent}" ]
            }
            case "$*" in
                *daemon-reload*)
                    : > "${RELOAD_STAMP:-/dev/null}"
                    ;;
                *CPUQuotaPerSecUSec*)
                    if reloaded && [ -n "${FAKE_QUOTA_AFTER_RELOAD:-}" ]; then
                        printf '%s\\n' "$FAKE_QUOTA_AFTER_RELOAD"
                    else
                        printf '%s\\n' "${FAKE_QUOTA:-4s}"
                    fi
                    ;;
                *MemoryMax*)
                    if reloaded && [ -n "${FAKE_MEMORY_MAX_AFTER_RELOAD:-}" ]; then
                        printf '%s\\n' "$FAKE_MEMORY_MAX_AFTER_RELOAD"
                    else
                        printf '%s\\n' "${FAKE_MEMORY_MAX:-25769803776}"
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
                printf '%s\n' "$1" >> "$CAPTURE"
                if [ "$1" = "--" ]; then
                    shift
                    exec "$@"
                fi
                shift
            done
            exit 2
            """,
        )
        self.write_executable(
            "probe",
            """
            #!/bin/sh
            printf 'argument=%s\n' "$1"
            printf 'marker=%s\n' "$MARKER"
            printf 'test-shims=%s\n' "$NKS_AGENT_TEST_SHIMS_ACTIVE"
            printf 'original-path=%s\n' "$NKS_AGENT_TEST_ORIGINAL_PATH"
            printf 'path=%s\n' "$PATH"
            pwd
            """,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_executable(self, name: str, source: str) -> None:
        path = self.bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def environment(self) -> dict[str, str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("NKS_AGENT_TEST_")
        }
        return {
            **environment,
            "CAPTURE": str(self.capture),
            "RELOAD_STAMP": str(self.reload_stamp),
            "MARKER": "preserved",
            "PATH": f"{self.bin}:/usr/bin:/bin",
        }

    def test_launches_command_in_aggregate_slice(self) -> None:
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
        self.assertIn("marker=preserved", result.stdout)
        self.assertIn("test-shims=1", result.stdout)
        self.assertIn(
            f"original-path={self.bin}:/usr/bin:/bin",
            result.stdout,
        )
        self.assertIn(
            f"path={SCRIPT.parents[1] / 'libexec' / 'agent-test-shims'}:"
            f"{self.bin}:/usr/bin:/bin",
            result.stdout,
        )
        self.assertIn(str(self.root), result.stdout)
        self.assertEqual(
            self.capture.read_text(encoding="utf-8").splitlines(),
            [
                "--user",
                "--scope",
                "--quiet",
                "--collect",
                "--same-dir",
                "--slice=agents.slice",
                "--",
            ],
        )

    def test_stale_active_marker_does_not_disable_test_shims(self) -> None:
        environment = self.environment()
        environment["NKS_AGENT_TEST_SHIMS_ACTIVE"] = "1"

        result = subprocess.run(
            [str(SCRIPT), "probe", "marker"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            f"path={SCRIPT.parents[1] / 'libexec' / 'agent-test-shims'}:",
            result.stdout,
        )
        self.assertIn(
            f"original-path={self.bin}:/usr/bin:/bin",
            result.stdout,
        )

    def test_existing_shim_path_reconstructs_original_path(self) -> None:
        shim = SCRIPT.parents[1] / "libexec" / "agent-test-shims"
        environment = self.environment()
        environment["PATH"] = f"{shim}:{self.bin}:{shim}:/usr/bin:/bin"

        result = subprocess.run(
            [str(SCRIPT), "probe", "existing-shim"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            f"original-path={self.bin}:/usr/bin:/bin",
            result.stdout,
        )
        self.assertIn(
            f"path={shim}:{self.bin}:/usr/bin:/bin",
            result.stdout,
        )

    def test_refuses_to_run_without_expected_quota(self) -> None:
        environment = self.environment()
        environment["FAKE_QUOTA"] = "infinity"

        result = subprocess.run(
            [str(SCRIPT), "probe", "ignored"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("does not have a finite CPU limit", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_refuses_to_run_without_expected_memory_limit(self) -> None:
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
        self.assertTrue(self.reload_stamp.exists())
        self.assertFalse(self.capture.exists())

    def test_daemon_reload_recovers_stale_limits(self) -> None:
        environment = self.environment()
        environment["FAKE_MEMORY_MAX"] = "infinity"
        environment["FAKE_MEMORY_MAX_AFTER_RELOAD"] = "25769803776"

        result = subprocess.run(
            [str(SCRIPT), "probe", "recovered"],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("argument=recovered", result.stdout)
        self.assertTrue(self.reload_stamp.exists())
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
