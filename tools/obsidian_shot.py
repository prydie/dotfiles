#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_obsidian(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["obsidian", *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def js_string(value: str) -> str:
    return json.dumps(value)


def output_path(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(f"/tmp/obsidian-shot-{stamp}.png")


def wait_for_selector(selector: str, timeout_ms: int) -> int:
    deadline = time.monotonic() + (timeout_ms / 1000)
    last_count = 0

    while time.monotonic() < deadline:
        last_count = visible_match_count(selector)
        if last_count > 0:
            return last_count

        time.sleep(0.25)

    return last_count


def visible_match_count(selector: str) -> int:
    code = (
        "(() => Array.from(document.querySelectorAll("
        f"{js_string(selector)}"
        ")).filter((e) => {"
        "const r = e.getBoundingClientRect();"
        "const s = getComputedStyle(e);"
        "return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';"
        "}).length)()"
    )
    result = run_obsidian(["eval", f"code={code}"], check=False)
    if result.returncode != 0:
        return 0

    value = result.stdout.strip().removeprefix("=> ").strip()
    try:
        return int(value)
    except ValueError:
        return 0


def visible_element_script(selector: str) -> str:
    return (
        "Array.from(document.querySelectorAll("
        f"{js_string(selector)}"
        ")).find((e) => {"
        "const r = e.getBoundingClientRect();"
        "const s = getComputedStyle(e);"
        "return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';"
        "})"
    )


def scroll_selector_into_view(selector: str) -> None:
    code = (
        "(() => {"
        f"const e = {visible_element_script(selector)};"
        "if (!e) return 'not found';"
        "e.scrollIntoView({block: 'center', inline: 'center'});"
        "return 'ok';"
        "})()"
    )
    run_obsidian(["eval", f"code={code}"], check=False)


def selector_metrics(selector: str) -> str:
    code = (
        "(() => {"
        f"const e = {visible_element_script(selector)};"
        "if (!e) return JSON.stringify({found:false});"
        "const r = e.getBoundingClientRect();"
        "return JSON.stringify({"
        "found:true,"
        "x:Math.round(r.x),"
        "y:Math.round(r.y),"
        "width:Math.round(r.width),"
        "height:Math.round(r.height),"
        "viewportWidth:window.innerWidth,"
        "viewportHeight:window.innerHeight"
        "});"
        "})()"
    )
    result = run_obsidian(["eval", f"code={code}"], check=False)
    return result.stdout.strip().removeprefix("=> ").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="obsidian-shot",
        description="Open an Obsidian note, scroll to a selector, and capture the app window."
    )
    parser.add_argument("path", nargs="?", help="Vault-relative note path to open")
    parser.add_argument("-o", "--output", help="Screenshot output path")
    parser.add_argument("--vault", help="Obsidian vault name")
    parser.add_argument(
        "--selector",
        default=".workspace-leaf.mod-active .view-content",
        help="CSS selector to wait for and scroll into view (default: active view content)",
    )
    parser.add_argument(
        "--wait-selector",
        help="CSS selector to wait for before capture (defaults to --selector)",
    )
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="Obsidian command ID to execute after opening the note; repeatable",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=10000,
        help="Maximum time to wait for selector rendering (default: 10000)",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=500,
        help="Delay after scrolling before screenshot capture (default: 500)",
    )
    parser.add_argument(
        "--no-scroll",
        action="store_true",
        help="Do not scroll the selector into view before capture",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print result metadata as JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = output_path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)

    if args.path:
        open_args = ["open", f"path={args.path}"]
        if args.vault:
            open_args.append(f"vault={args.vault}")
        run_obsidian(open_args)

    for command in args.command:
        run_obsidian(["command", f"id={command}"])

    wait_selector = args.wait_selector or args.selector
    count = wait_for_selector(wait_selector, args.timeout_ms)
    if count == 0:
        print(f"Timed out waiting for selector: {wait_selector}", file=sys.stderr)
        print(
            "If the note is in source mode, switch it to reading mode or pass --command markdown:toggle-preview.",
            file=sys.stderr,
        )
        return 1

    if not args.no_scroll:
        scroll_selector_into_view(args.selector)
        time.sleep(args.settle_ms / 1000)

    run_obsidian(["dev:screenshot", f"path={target}"])
    metrics = selector_metrics(args.selector)

    if args.json:
        print(
            json.dumps(
                {
                    "output": str(target),
                    "selector": args.selector,
                    "waitSelector": wait_selector,
                    "matches": count,
                    "metrics": json.loads(metrics),
                },
                sort_keys=True,
            )
        )
    else:
        print(metrics)
        print(target)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
