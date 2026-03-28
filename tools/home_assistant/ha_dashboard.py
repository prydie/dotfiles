#!/usr/bin/env python3
"""Manage Home Assistant Lovelace dashboards via the websocket API.

The tool is intentionally generic enough for ad-hoc personal operations:
- fetch the current dashboard config
- upsert a card by title into a chosen view
- avoid direct `.storage` edits and Home Assistant restarts

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
import sys
from typing import Any
from urllib.parse import urlparse


DEFAULT_HA_URL = os.environ.get("HOME_ASSISTANT_URL", "http://192.168.1.252:8123")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_HA_URL, help="Home Assistant base URL")
    parser.add_argument(
        "--token",
        default=os.environ.get("HOME_ASSISTANT_TOKEN", ""),
        help="Home Assistant long-lived token (defaults to HOME_ASSISTANT_TOKEN)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    get_config = subparsers.add_parser("get-config", help="Fetch a Lovelace dashboard config")
    get_config.add_argument(
        "--dashboard",
        default="",
        help="Dashboard URL path (`lovelace` is accepted as an alias for the default dashboard)",
    )
    get_config.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the returned JSON",
    )
    set_config = subparsers.add_parser("set-config", help="Save a full Lovelace dashboard config")
    set_config.add_argument(
        "--dashboard",
        default="",
        help="Dashboard URL path (`lovelace` is accepted as an alias for the default dashboard)",
    )
    config_group = set_config.add_mutually_exclusive_group(required=True)
    config_group.add_argument("--config-file", help="Path to a JSON file containing a full dashboard config")
    config_group.add_argument("--config-json", help="Inline JSON containing a full dashboard config")

    upsert_card = subparsers.add_parser("upsert-card", help="Insert or replace a card by title")
    upsert_card.add_argument(
        "--dashboard",
        default="",
        help="Dashboard URL path (`lovelace` is accepted as an alias for the default dashboard)",
    )
    upsert_card.add_argument("--view-path", default="", help="View path to edit")
    upsert_card.add_argument("--view-title", default="", help="View title to edit")
    upsert_card.add_argument("--title", required=True, help="Card title to replace or insert")
    upsert_card.add_argument(
        "--after-title",
        default="",
        help="Insert after the card with this title when creating a new card",
    )
    group = upsert_card.add_mutually_exclusive_group(required=True)
    group.add_argument("--card-file", help="Path to a JSON file containing a single card object")
    group.add_argument("--card-json", help="Inline JSON for a single card object")

    replace_card = subparsers.add_parser(
        "replace-card-entity",
        help="Recursively replace the first card matching an entity ID",
    )
    replace_card.add_argument(
        "--dashboard",
        default="",
        help="Dashboard URL path (`lovelace` is accepted as an alias for the default dashboard)",
    )
    replace_card.add_argument("--view-path", default="", help="View path to edit")
    replace_card.add_argument("--view-title", default="", help="View title to edit")
    replace_card.add_argument("--entity", required=True, help="Card entity ID to replace")
    replace_group = replace_card.add_mutually_exclusive_group(required=True)
    replace_group.add_argument("--card-file", help="Path to a JSON file containing a single card object")
    replace_group.add_argument("--card-json", help="Inline JSON for a single card object")

    return parser.parse_args()


def require_token(token: str) -> str:
    resolved = token.strip()
    if not resolved:
        raise SystemExit("HOME_ASSISTANT_TOKEN or --token is required")
    return resolved


def load_card(args: argparse.Namespace) -> dict[str, Any]:
    raw = args.card_json
    if args.card_file:
        raw = Path(args.card_file).read_text()
    assert raw is not None
    try:
        card = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid card JSON: {exc}") from exc
    if not isinstance(card, dict):
        raise SystemExit("card JSON must describe a single object")
    return card


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
        raise SystemExit("dashboard config JSON must describe a single object")
    return config


def resolve_websocket_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"invalid Home Assistant URL: {base_url}")
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    path = parsed.path.rstrip("/")
    return f"{ws_scheme}://{parsed.netloc}{path}/api/websocket"


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
    response = await websocket_request(
        base_url,
        token,
        message,
    )
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
    await websocket_request(
        base_url,
        token,
        message,
    )


def normalize_dashboard(dashboard: str) -> str:
    text = dashboard.strip()
    if text == "lovelace":
        return ""
    return text


def find_view(config: dict[str, Any], view_path: str, view_title: str) -> dict[str, Any]:
    views = config.get("views")
    if not isinstance(views, list):
        raise SystemExit("dashboard config does not contain a views list")

    if view_path:
        for view in views:
            if isinstance(view, dict) and view.get("path") == view_path:
                return view
        raise SystemExit(f"no view found with path {view_path!r}")

    if view_title:
        for view in views:
            if isinstance(view, dict) and view.get("title") == view_title:
                return view
        raise SystemExit(f"no view found with title {view_title!r}")

    if not views:
        raise SystemExit("dashboard has no views")
    if not isinstance(views[0], dict):
        raise SystemExit("first dashboard view is not an object")
    return views[0]


def upsert_card_in_view(
    view: dict[str, Any],
    title: str,
    after_title: str,
    card: dict[str, Any],
) -> None:
    cards = view.setdefault("cards", [])
    if not isinstance(cards, list):
        raise SystemExit("target view does not have a cards list")

    for index, existing in enumerate(cards):
        if isinstance(existing, dict) and existing.get("title") == title:
            cards[index] = card
            return

    if after_title:
        for index, existing in enumerate(cards):
            if isinstance(existing, dict) and existing.get("title") == after_title:
                cards.insert(index + 1, card)
                return

    cards.append(card)


def replace_card_by_entity(cards: list[Any], entity_id: str, replacement: dict[str, Any]) -> bool:
    for index, existing in enumerate(cards):
        if isinstance(existing, dict):
            if existing.get("entity") == entity_id:
                cards[index] = replacement
                return True

            child_cards = existing.get("cards")
            if isinstance(child_cards, list) and replace_card_by_entity(child_cards, entity_id, replacement):
                return True

            inner_card = existing.get("card")
            if isinstance(inner_card, dict) and inner_card.get("entity") == entity_id:
                existing["card"] = replacement
                return True

    return False


async def run(args: argparse.Namespace) -> int:
    token = require_token(args.token)

    if args.command == "get-config":
        config = await fetch_dashboard_config(args.url, token, args.dashboard)
        dump = json.dumps(config, indent=2 if args.pretty else None)
        print(dump)
        return 0

    if args.command == "set-config":
        config = load_dashboard_config(args)
        await save_dashboard_config(args.url, token, args.dashboard, config)
        target = args.dashboard or "lovelace"
        print(f"Updated dashboard {target!r}.")
        return 0

    if args.command == "upsert-card":
        config = await fetch_dashboard_config(args.url, token, args.dashboard)
        view = find_view(config, args.view_path, args.view_title)
        card = load_card(args)
        if card.get("title") != args.title:
            card = dict(card)
            card["title"] = args.title
        upsert_card_in_view(view, args.title, args.after_title, card)
        await save_dashboard_config(args.url, token, args.dashboard, config)
        print(f"Updated card {args.title!r} in dashboard {args.dashboard!r}.")
        return 0

    if args.command == "replace-card-entity":
        config = await fetch_dashboard_config(args.url, token, args.dashboard)
        view = find_view(config, args.view_path, args.view_title)
        cards = view.get("cards")
        if not isinstance(cards, list):
            raise SystemExit("target view does not have a cards list")
        replacement = load_card(args)
        if not replace_card_by_entity(cards, args.entity, replacement):
            raise SystemExit(f"no card found with entity {args.entity!r}")
        await save_dashboard_config(args.url, token, args.dashboard, config)
        print(f"Replaced card for entity {args.entity!r} in dashboard {args.dashboard!r}.")
        return 0

    raise SystemExit(f"unsupported command: {args.command}")


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
