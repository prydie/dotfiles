#!/usr/bin/env python3
"""Capture webpage screenshots with headless Chrome."""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 2200
DEFAULT_TIMEOUT_MS = 5000
PROFILE_EXCLUDES = [
    "Singleton*",
    "*/Cache",
    "*/Cache/*",
    "*/Code Cache",
    "*/Code Cache/*",
    "*/GPUCache",
    "*/GPUCache/*",
    "*/Service Worker/CacheStorage",
    "*/Service Worker/CacheStorage/*",
    "*/blob_storage",
    "*/blob_storage/*",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Page URL to capture")
    parser.add_argument(
        "-o",
        "--output",
        help="Output image path (defaults to /tmp/webshot-<host>-<timestamp>.png)",
    )
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Viewport width in px")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Viewport height in px")
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help="Virtual time budget to allow the page to settle before capture",
    )
    parser.add_argument(
        "--user-data-dir",
        help="Chrome profile directory to reuse for authenticated sessions",
    )
    parser.add_argument(
        "--clone-user-data-dir-from",
        help="Clone an existing Chrome user data dir into a temporary copy before capture",
    )
    parser.add_argument(
        "--profile-directory",
        help="Chrome profile name within the user data dir, e.g. Default or Profile 1",
    )
    parser.add_argument(
        "--chrome-binary",
        default="google-chrome",
        help="Chrome binary to invoke",
    )
    parser.add_argument(
        "--no-sandbox",
        action="store_true",
        help="Pass --no-sandbox to Chrome (useful in restricted container environments)",
    )
    return parser.parse_args()


def default_output_path(url: str) -> Path:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_") or "page"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("/tmp") / f"webshot-{host}-{timestamp}.png"


def build_command(args: argparse.Namespace, output_path: Path, user_data_dir: str) -> list[str]:
    command = [
        args.chrome_binary,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--window-size={args.width},{args.height}",
        f"--virtual-time-budget={args.timeout_ms}",
        f"--screenshot={output_path}",
        f"--user-data-dir={user_data_dir}",
        args.url,
    ]
    if args.profile_directory:
        command.insert(-1, f"--profile-directory={args.profile_directory}")
    if args.no_sandbox:
        command.insert(1, "--no-sandbox")
    return command


def resolve_chrome(binary: str) -> str:
    resolved = shutil.which(binary)
    if not resolved:
        raise SystemExit(f"Chrome binary not found: {binary}")
    return resolved


def should_ignore(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in PROFILE_EXCLUDES)


def clone_user_data_dir(source_root: Path, target_root: Path, profile_directory: str | None) -> None:
    source_root = source_root.expanduser()
    if not source_root.exists():
        raise SystemExit(f"Chrome user data dir not found: {source_root}")

    items_to_copy = ["Local State"]
    if profile_directory:
        items_to_copy.append(profile_directory)

    for item_name in items_to_copy:
        source_path = source_root / item_name
        if not source_path.exists():
            continue
        target_path = target_root / item_name
        if source_path.is_dir():
            for path in source_path.rglob("*"):
                rel = path.relative_to(source_root)
                if should_ignore(str(rel)):
                    continue
                destination = target_root / rel
                if path.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)


def main() -> int:
    args = parse_args()
    args.chrome_binary = resolve_chrome(args.chrome_binary)

    output_path = Path(args.output).expanduser() if args.output else default_output_path(args.url)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.clone_user_data_dir_from:
        cleanup_dir = tempfile.TemporaryDirectory(prefix="webshot-chrome-profile-")
        user_data_dir = cleanup_dir.name
        clone_user_data_dir(
            Path(args.clone_user_data_dir_from),
            Path(user_data_dir),
            args.profile_directory,
        )
    elif args.user_data_dir:
        user_data_dir = str(Path(args.user_data_dir).expanduser())
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        cleanup_dir = None
    else:
        cleanup_dir = tempfile.TemporaryDirectory(prefix="webshot-chrome-")
        user_data_dir = cleanup_dir.name

    command = build_command(args, output_path, user_data_dir)
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    finally:
        if cleanup_dir is not None:
            cleanup_dir.cleanup()

    if completed.returncode != 0:
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        return completed.returncode

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
