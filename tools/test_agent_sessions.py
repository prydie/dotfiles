from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "bin" / "agent-sessions"
LOADER = importlib.machinery.SourceFileLoader("agent_sessions", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
agent_sessions = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = agent_sessions
LOADER.exec_module(agent_sessions)


class AgentSessionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.environment = mock.patch.dict(
            os.environ,
            {
                "AGENT_SESSIONS_STATE_DIR": str(self.root / "state"),
                "AGENT_SESSIONS_CLAUDE_HOME": str(self.root / "claude"),
                "AGENT_SESSIONS_PROC_ROOT": str(self.root / "proc"),
                "CODEX_HOME": str(self.root / "codex"),
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    @staticmethod
    def pane(pid: int = 123) -> object:
        return agent_sessions.Pane(
            pane_id="%7",
            session_name="project",
            window_index=2,
            pane_index=1,
            pid=pid,
            command="claude",
            cwd="/work/project",
        )

    def test_hook_records_only_resume_metadata(self) -> None:
        session_id = "d482bddb-7d8b-4514-b810-b90c3b01c8bd"
        payload = {
            "session_id": session_id,
            "transcript_path": "/private/transcript.jsonl",
            "cwd": "/work/project",
            "hook_event_name": "SessionStart",
        }
        stdin = io.StringIO(json.dumps(payload))
        with (
            mock.patch.dict(os.environ, {"TMUX_PANE": "%7"}),
            mock.patch.object(
                agent_sessions, "tmux_metadata", return_value=self.pane()
            ),
            mock.patch.object(agent_sessions.sys, "stdin", stdin),
        ):
            self.assertEqual(agent_sessions.record_hook("claude"), 0)

        record = json.loads(
            agent_sessions.active_record_path("%7").read_text(encoding="utf-8")
        )
        self.assertEqual(record["session_id"], session_id)
        self.assertEqual(record["pane_pid"], 123)
        self.assertNotIn("transcript_path", record)

    def test_stale_hook_record_does_not_match_reused_pane(self) -> None:
        pane = self.pane(pid=999)
        path = agent_sessions.active_record_path(pane.pane_id)
        agent_sessions.atomic_json_write(
            path,
            {
                "version": 1,
                "agent": "claude",
                "pane_id": pane.pane_id,
                "pane_pid": 123,
                "session_id": "d482bddb-7d8b-4514-b810-b90c3b01c8bd",
                "cwd": pane.cwd,
            },
        )
        self.assertIsNone(agent_sessions.active_record(pane, "claude"))

    def test_recovers_claude_session_from_pid_registry(self) -> None:
        process = agent_sessions.AgentProcess("claude", 456, ("claude",))
        registry = Path(os.environ["AGENT_SESSIONS_CLAUDE_HOME"]) / "sessions"
        registry.mkdir(parents=True)
        (registry / "456.json").write_text(
            json.dumps(
                {
                    "pid": 456,
                    "sessionId": "37a9c032-bd58-4de0-9f8e-5cf805a56518",
                    "cwd": "/work/project",
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(
            agent_sessions.claude_process_state(process),
            ("37a9c032-bd58-4de0-9f8e-5cf805a56518", "/work/project"),
        )

    def test_recovers_codex_session_from_open_top_level_transcript(self) -> None:
        session_id = "019f6552-9c4b-78d0-8d8e-2d6919e3ddf0"
        sessions = Path(os.environ["CODEX_HOME"]) / "sessions" / "2026" / "07" / "15"
        sessions.mkdir(parents=True)
        transcript = sessions / f"rollout-{session_id}.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": session_id,
                        "cwd": "/work/project",
                        "originator": "codex-tui",
                        "source": "cli",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        descriptors = Path(os.environ["AGENT_SESSIONS_PROC_ROOT"]) / "789" / "fd"
        descriptors.mkdir(parents=True)
        (descriptors / "8").symlink_to(transcript)
        process = agent_sessions.AgentProcess("codex", 789, ("codex",))
        pane = self.pane(pid=789)
        self.assertEqual(
            agent_sessions.codex_open_session(process, pane),
            (session_id, "/work/project"),
        )

    def test_hook_install_is_additive_and_idempotent(self) -> None:
        claude_settings = (
            Path(os.environ["AGENT_SESSIONS_CLAUDE_HOME"]) / "settings.json"
        )
        claude_settings.parent.mkdir(parents=True)
        claude_settings.write_text(
            json.dumps({"theme": "dark", "hooks": {"PreToolUse": []}}),
            encoding="utf-8",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            agent_sessions.install_hooks()
            first = claude_settings.read_text(encoding="utf-8")
            agent_sessions.install_hooks()
            second = claude_settings.read_text(encoding="utf-8")

        self.assertEqual(first, second)
        settings = json.loads(second)
        self.assertEqual(settings["theme"], "dark")
        self.assertIn("PreToolUse", settings["hooks"])
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)
        self.assertEqual(len(settings["hooks"]["SessionEnd"]), 1)
        codex_hooks = json.loads(
            (Path(os.environ["CODEX_HOME"]) / "hooks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(codex_hooks["hooks"]["SessionStart"]), 1)
        self.assertEqual(len(codex_hooks["hooks"]["Stop"]), 1)

    def test_resume_commands_use_native_cli_interfaces(self) -> None:
        session_id = "019f6552-9c4b-78d0-8d8e-2d6919e3ddf0"
        self.assertEqual(
            agent_sessions.resume_argv("codex", session_id),
            ["codex", "resume", session_id],
        )
        self.assertEqual(
            agent_sessions.resume_argv("claude", session_id),
            ["claude", "--resume", session_id],
        )
        self.assertEqual(
            agent_sessions.resume_argv(
                "codex", session_id, "unix:///tmp/codex-app-server.sock"
            ),
            [
                "codex",
                "resume",
                "--remote",
                "unix:///tmp/codex-app-server.sock",
                session_id,
            ],
        )

    def test_scoped_agent_command_uses_adjacent_launcher(self) -> None:
        self.assertEqual(
            agent_sessions.scoped_agent_argv(["claude", "--resume", "session"]),
            [
                str(SCRIPT.resolve().with_name("agent-run")),
                "claude",
                "--resume",
                "session",
            ],
        )

    def test_managed_daemon_starts_inside_agent_slice(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(
            agent_sessions.subprocess, "run", return_value=result
        ) as run:
            agent_sessions.manage_codex_daemon("start")

        self.assertEqual(
            run.call_args.args[0],
            [
                str(SCRIPT.resolve().with_name("agent-run")),
                "codex",
                "app-server",
                "daemon",
                "start",
            ],
        )

    def test_managed_daemon_stop_does_not_create_an_agent_scope(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(
            agent_sessions.subprocess, "run", return_value=result
        ) as run:
            agent_sessions.manage_codex_daemon("stop")

        self.assertEqual(
            run.call_args.args[0], ["codex", "app-server", "daemon", "stop"]
        )

    def test_detects_codex_remote_attachment(self) -> None:
        process = agent_sessions.AgentProcess(
            "codex",
            789,
            (
                "codex",
                "resume",
                "--remote",
                "unix:///tmp/codex-app-server.sock",
                "--all",
            ),
        )
        self.assertEqual(
            agent_sessions.remote_address(process),
            "unix:///tmp/codex-app-server.sock",
        )

    def test_recognizes_managed_codex_daemon_socket(self) -> None:
        socket = (
            Path(os.environ["CODEX_HOME"])
            / "app-server-control"
            / "app-server-control.sock"
        )
        self.assertTrue(agent_sessions.managed_daemon_remote(f"unix://{socket}"))
        self.assertFalse(agent_sessions.managed_daemon_remote("unix:///tmp/other.sock"))

    def test_checkpoint_stops_managed_daemon_after_panes_exit(self) -> None:
        socket = (
            Path(os.environ["CODEX_HOME"])
            / "app-server-control"
            / "app-server-control.sock"
        )
        pane = self.pane(pid=789)
        process = agent_sessions.AgentProcess("codex", 789, ("codex",))
        resolution = agent_sessions.Resolution(
            pane=pane,
            process=process,
            session_id="019f6552-9c4b-78d0-8d8e-2d6919e3ddf0",
            cwd=pane.cwd,
            method="manual",
            remote=f"unix://{socket}",
        )
        arguments = SimpleNamespace(keep_running=False, yes=True, timeout=1.0)
        with (
            mock.patch.object(
                agent_sessions, "active_resolutions", return_value=[resolution]
            ),
            mock.patch.object(agent_sessions, "save_tmux_layout"),
            mock.patch.object(
                agent_sessions,
                "write_snapshot",
                return_value=self.root / "checkpoint.json",
            ),
            mock.patch.object(agent_sessions, "stop_agents", return_value=[]),
            mock.patch.object(agent_sessions, "manage_codex_daemon") as manage,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(agent_sessions.checkpoint(arguments), 0)
        manage.assert_called_once_with("stop")

    def test_shutdown_does_not_send_exit_after_ctrl_c_closed_agent(self) -> None:
        pane = self.pane(pid=789)
        process = agent_sessions.AgentProcess("codex", 789, ("codex",))
        resolution = agent_sessions.Resolution(
            pane=pane,
            process=process,
            session_id="019f6552-9c4b-78d0-8d8e-2d6919e3ddf0",
            cwd=pane.cwd,
            method="hook",
            remote=None,
        )
        with (
            mock.patch.object(
                agent_sessions, "wait_for_agent_exit", return_value=set()
            ),
            mock.patch.object(agent_sessions, "run_tmux") as run_tmux,
            mock.patch.object(agent_sessions, "send_agent_exit") as send_exit,
        ):
            self.assertEqual(agent_sessions.stop_agents([resolution], 30), [])
        send_exit.assert_not_called()
        self.assertEqual(run_tmux.call_args.args[3], "C-c")

    def test_shutdown_retries_slow_agent_without_force_killing(self) -> None:
        pane = self.pane(pid=789)
        process = agent_sessions.AgentProcess("claude", 789, ("claude",))
        resolution = agent_sessions.Resolution(
            pane=pane,
            process=process,
            session_id="37a9c032-bd58-4de0-9f8e-5cf805a56518",
            cwd=pane.cwd,
            method="hook",
            remote=None,
        )
        remaining = {pane.pane_id}
        with (
            mock.patch.object(
                agent_sessions,
                "wait_for_agent_exit",
                side_effect=[remaining, remaining, remaining, set()],
            ),
            mock.patch.object(agent_sessions, "run_tmux") as run_tmux,
            mock.patch.object(agent_sessions, "send_agent_exit") as send_exit,
        ):
            self.assertEqual(agent_sessions.stop_agents([resolution], 30), [])
        self.assertEqual(send_exit.call_count, 2)
        self.assertEqual(
            sum(call.args[3] == "C-c" for call in run_tmux.call_args_list), 2
        )

    def test_restore_can_replace_the_pane_running_restore(self) -> None:
        pane = self.pane(pid=789)
        pane = agent_sessions.dataclasses.replace(pane, command="python3")
        session_id = "37a9c032-bd58-4de0-9f8e-5cf805a56518"
        snapshot = self.root / "latest.json"
        agent_sessions.atomic_json_write(
            snapshot,
            {
                "captured_at": "2026-07-15T11:36:45+00:00",
                "panes": [
                    {
                        "agent": "claude",
                        "cwd": pane.cwd,
                        "pane_index": pane.pane_index,
                        "session_id": session_id,
                        "tmux_session": pane.session_name,
                        "window_index": pane.window_index,
                    }
                ],
                "version": 1,
            },
        )
        arguments = SimpleNamespace(snapshot=str(snapshot), run=True, yes=True)
        with (
            mock.patch.dict(os.environ, {"TMUX_PANE": pane.pane_id}),
            mock.patch.object(agent_sessions, "list_panes", return_value=[pane]),
            mock.patch.object(agent_sessions, "run_tmux") as run_tmux,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(agent_sessions.restore(arguments), 0)
        sent = [call.args for call in run_tmux.call_args_list]
        resumed = [
            " ".join(call)
            for call in sent
            if "claude --resume" in " ".join(call)
        ]
        self.assertEqual(len(resumed), 1)
        self.assertIn("agent-run", resumed[0])

    def test_secures_resurrect_directory_and_snapshots(self) -> None:
        directory = self.root / "resurrect"
        directory.mkdir(mode=0o775)
        current = directory / "tmux_resurrect_20260715T123644.txt"
        previous = directory / "tmux_resurrect_20260715T120420.txt"
        current.write_text("current\n", encoding="utf-8")
        previous.write_text("previous\n", encoding="utf-8")
        current.chmod(0o664)
        previous.chmod(0o664)

        self.assertEqual(agent_sessions.secure_resurrect_state(str(current)), 0)

        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual(current.stat().st_mode & 0o777, 0o600)
        self.assertEqual(previous.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
