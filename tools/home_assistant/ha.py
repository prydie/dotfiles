#!/usr/bin/env python3
"""Small Home Assistant CLI for personal ops and dashboard tooling.

Authentication:
- `HOME_ASSISTANT_TOKEN` must contain a long-lived access token
- `HOME_ASSISTANT_URL` defaults to `http://192.168.1.252:8123`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


DEFAULT_HA_URL = os.environ.get("HOME_ASSISTANT_URL", "http://192.168.1.252:8123").rstrip("/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_HA_URL, help="Home Assistant base URL")
    parser.add_argument(
        "--token",
        default=os.environ.get("HOME_ASSISTANT_TOKEN", ""),
        help="Home Assistant long-lived token (defaults to HOME_ASSISTANT_TOKEN)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    state = subparsers.add_parser("state", help="Fetch a single entity state")
    state.add_argument("entity_id")
    state.add_argument("--json", action="store_true", help="Print the full state object as JSON")

    attrs = subparsers.add_parser("attrs", help="Fetch a single entity's attributes")
    attrs.add_argument("entity_id")
    attrs.add_argument("--json", action="store_true", help="Print raw JSON instead of pretty output")

    search = subparsers.add_parser("search", help="Search entities by ID")
    search.add_argument("pattern")
    search.add_argument("--regex", action="store_true", help="Treat PATTERN as a regular expression")
    search.add_argument(
        "--json",
        action="store_true",
        help="Print matched full state objects as JSON instead of one entity ID per line",
    )

    service = subparsers.add_parser("service", help="Call a Home Assistant service")
    service.add_argument("service", help="Service in the form domain.service")
    service.add_argument("--data", default="{}", help="JSON payload to send to the service")
    service.add_argument("--json", action="store_true", help="Print the raw JSON result")

    dashboard = subparsers.add_parser("dashboard", help="Dashboard operations")
    dashboard_subparsers = dashboard.add_subparsers(dest="dashboard_command", required=True)
    get_config = dashboard_subparsers.add_parser("get-config", help="Fetch dashboard config")
    get_config.add_argument(
        "--dashboard",
        default="",
        help="Dashboard URL path (`lovelace` is accepted as an alias for the default dashboard)",
    )
    get_config.add_argument("--pretty", action="store_true", help="Pretty-print the returned JSON")
    set_config = dashboard_subparsers.add_parser("set-config", help="Save dashboard config")
    set_config.add_argument(
        "--dashboard",
        default="",
        help="Dashboard URL path (`lovelace` is accepted as an alias for the default dashboard)",
    )
    group = set_config.add_mutually_exclusive_group(required=True)
    group.add_argument("--config-file", help="Path to a JSON file containing the full dashboard config")
    group.add_argument("--config-json", help="Inline JSON containing the full dashboard config")

    return parser.parse_args()


def require_token(token: str) -> str:
    resolved = token.strip()
    if not resolved:
        raise SystemExit("HOME_ASSISTANT_TOKEN or --token is required")
    return resolved


def build_rest_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def rest_request(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(build_rest_url(base_url, path), data=data, headers=headers, method=method)
    with urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        if not body:
            return None
        return json.loads(body)


def resolve_websocket_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"invalid Home Assistant URL: {base_url}")
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    path = parsed.path.rstrip("/")
    return f"{ws_scheme}://{parsed.netloc}{path}/api/websocket"


def normalize_dashboard(dashboard: str) -> str:
    text = dashboard.strip()
    if text == "lovelace":
        return ""
    return text


async def websocket_request(base_url: str, token: str, message: dict[str, Any]) -> dict[str, Any]:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "The 'websockets' package is required. Run `uv sync` in ~/.dotfiles first."
        ) from exc

    ws_url = resolve_websocket_url(base_url)
    async with websockets.connect(ws_url) as websocket:
        auth_required = json.loads(await websocket.recv())
        if auth_required.get("type") != "auth_required":
            raise SystemExit(f"unexpected websocket handshake: {auth_required!r}")

        await websocket.send(json.dumps({"type": "auth", "access_token": token}))
        auth_ok = json.loads(await websocket.recv())
        if auth_ok.get("type") != "auth_ok":
            raise SystemExit(f"websocket auth failed: {auth_ok!r}")

        payload = {"id": 1, **message}
        await websocket.send(json.dumps(payload))
        response = json.loads(await websocket.recv())
        if not response.get("success", False):
            raise SystemExit(f"Home Assistant request failed: {response!r}")
        return response


async def fetch_dashboard_config(base_url: str, token: str, dashboard: str) -> dict[str, Any]:
    message: dict[str, Any] = {"type": "lovelace/config"}
    normalized = normalize_dashboard(dashboard)
    if normalized:
        message["url_path"] = normalized
    response = await websocket_request(base_url, token, message)
    return response["result"]


async def save_dashboard_config(
    base_url: str,
    token: str,
    dashboard: str,
    config: dict[str, Any],
) -> None:
    message: dict[str, Any] = {"type": "lovelace/config/save", "config": config}
    normalized = normalize_dashboard(dashboard)
    if normalized:
        message["url_path"] = normalized
    await websocket_request(base_url, token, message)


def load_dashboard_config(args: argparse.Namespace) -> dict[str, Any]:
    raw = args.config_json
    if args.config_file:
        raw = Path(args.config_file).read_text()
    assert raw is not None
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid dashboard JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise SystemExit("dashboard config JSON must describe an object")
    return config


def print_json(value: Any, *, pretty: bool = True) -> None:
    print(json.dumps(value, indent=2 if pretty else None, sort_keys=pretty))


def run_state(args: argparse.Namespace, token: str) -> int:
    result = rest_request(args.url, token, f"/api/states/{quote(args.entity_id, safe='._')}")
    if args.json:
        print_json(result)
    else:
        print(result.get("state", ""))
    return 0


def run_attrs(args: argparse.Namespace, token: str) -> int:
    result = rest_request(args.url, token, f"/api/states/{quote(args.entity_id, safe='._')}")
    attributes = result.get("attributes", {})
    if args.json:
        print_json(attributes)
    else:
        for key in sorted(attributes):
            print(f"{key}: {attributes[key]}")
    return 0


def run_search(args: argparse.Namespace, token: str) -> int:
    states = rest_request(args.url, token, "/api/states")
    if not isinstance(states, list):
        raise SystemExit("unexpected response from /api/states")

    if args.regex:
        matcher = re.compile(args.pattern)
        matches = [state for state in states if matcher.search(state.get("entity_id", ""))]
    else:
        matches = [state for state in states if args.pattern in state.get("entity_id", "")]

    if args.json:
        print_json(matches)
    else:
        for state in matches:
            print(state.get("entity_id", ""))
    return 0


def run_service(args: argparse.Namespace, token: str) -> int:
    if "." not in args.service:
        raise SystemExit("service must be in the form domain.service")
    domain, service_name = args.service.split(".", 1)
    try:
        payload = json.loads(args.data)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON for --data: {exc}") from exc
    result = rest_request(
        args.url,
        token,
        f"/api/services/{quote(domain, safe='')}/{quote(service_name, safe='')}",
        method="POST",
        payload=payload,
    )
    if args.json:
        print_json(result)
    else:
        print(f"Called {args.service}.")
    return 0


async def run_dashboard(args: argparse.Namespace, token: str) -> int:
    if args.dashboard_command == "get-config":
        config = await fetch_dashboard_config(args.url, token, args.dashboard)
        print(json.dumps(config, indent=2 if args.pretty else None))
        return 0
    if args.dashboard_command == "set-config":
        config = load_dashboard_config(args)
        await save_dashboard_config(args.url, token, args.dashboard, config)
        target = args.dashboard or "lovelace"
        print(f"Updated dashboard {target!r}.")
        return 0
    raise SystemExit(f"unsupported dashboard command: {args.dashboard_command}")


async def run(args: argparse.Namespace) -> int:
    token = require_token(args.token)
    if args.command == "state":
        return run_state(args, token)
    if args.command == "attrs":
        return run_attrs(args, token)
    if args.command == "search":
        return run_search(args, token)
    if args.command == "service":
        return run_service(args, token)
    if args.command == "dashboard":
        return await run_dashboard(args, token)
    raise SystemExit(f"unsupported command: {args.command}")


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
