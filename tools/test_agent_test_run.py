from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
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


if __name__ == "__main__":
    unittest.main()
