#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from pathlib import Path


DRM = Path("/sys/class/drm")
SRGB_PROFILE = Path("/usr/share/color/icc/colord/sRGB.icc")
TARGET_MODELS = ("DELL S2725QS", "BenQ EL2870U")


def run(*args: str) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        raise SystemExit(f"missing required command: {args[0]}")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.output.strip() or f"{args[0]} failed with {exc.returncode}")


def run_allowing(output_fragment: str, *args: str) -> str:
    try:
        return run(*args)
    except SystemExit as exc:
        message = str(exc)
        if output_fragment in message:
            return message
        raise


def edid_text(edid: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    if len(edid) < 128:
        return result

    for start in range(54, 126, 18):
        block = edid[start : start + 18]
        if len(block) != 18 or block[0:3] != b"\x00\x00\x00":
            continue

        tag = block[3]
        text = block[5:18].split(b"\n", 1)[0].decode("ascii", "ignore").strip()
        if not text:
            continue

        if tag == 0xFC:
            result["name"] = text
        elif tag == 0xFF:
            result["serial"] = text

    return result


def connected_outputs() -> list[dict[str, str]]:
    outputs = []
    for status in sorted(DRM.glob("card*-*/status")):
        if status.read_text().strip() != "connected":
            continue

        connector = status.parent.name.split("-", 1)[1]
        info = {"connector": connector}
        edid = status.parent / "edid"
        if edid.exists():
            info.update(edid_text(edid.read_bytes()))
        outputs.append(info)
    return outputs


def parse_colormgr_devices() -> list[dict[str, object]]:
    devices: list[dict[str, object]] = []
    current: dict[str, object] = {}
    profiles: list[str] = []
    last_metadata_key = ""

    for line in run("colormgr", "get-devices").splitlines():
        if line.startswith("Object Path:"):
            if current:
                current["profiles"] = profiles
                devices.append(current)
            current = {"object_path": line.split(":", 1)[1].strip()}
            profiles = []
            continue

        if not current:
            continue

        if ":" not in line:
            stripped = line.strip()
            if stripped.startswith("/"):
                profiles.append(stripped)
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()

        if key.startswith("profile_"):
            profiles.append(value)
        elif key == "metadata":
            meta_key, _, meta_value = value.partition("=")
            if meta_key:
                last_metadata_key = f"metadata_{meta_key.strip().lower()}"
                current[last_metadata_key] = meta_value.strip()
        elif last_metadata_key and line.startswith(" "):
            current[last_metadata_key] = f"{current[last_metadata_key]}\n{value}"
        else:
            last_metadata_key = ""
            current[key] = value

    if current:
        current["profiles"] = profiles
        devices.append(current)

    return [device for device in devices if device.get("type") == "display"]


def list_state(_: argparse.Namespace) -> None:
    print("Connected outputs")
    for output in connected_outputs():
        name = output.get("name", "unknown display")
        serial = output.get("serial", "unknown serial")
        print(f"  {output['connector']}: {name} ({serial})")

    print("\nColor-managed display devices")
    displays = parse_colormgr_devices()
    if not displays:
        print("  none")
        return

    for device in displays:
        model = device.get("model", "unknown model")
        vendor = device.get("vendor", "unknown vendor")
        xrandr = device.get("metadata_xrandr_name", "unknown output")
        device_id = device.get("device_id", "unknown device id")
        print(f"  {xrandr}: {vendor} {model}")
        print(f"    device: {device_id}")
        default = default_profile(str(device_id), exit_on_error=False)
        if default:
            print(f"    default: {profile_title(default)}")
        for profile in device.get("profiles", []):
            print(f"    profile: {profile}")


def import_profile(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"profile not found: {path}")

    output = run("colormgr", "import-profile", str(path.expanduser()))
    match = re.search(r"Object Path:\s*(\S+)", output)
    if match:
        return match.group(1)

    output = run("colormgr", "find-profile-by-filename", str(path.expanduser()))
    match = re.search(r"Object Path:\s*(\S+)", output)
    if not match:
        raise SystemExit(f"imported profile but could not find its colord object:\n{output}")
    return match.group(1)


def profile_by_filename(path: Path) -> str:
    output = run("colormgr", "find-profile-by-filename", str(path))
    match = re.search(r"Object Path:\s*(\S+)", output)
    if not match:
        raise SystemExit(f"could not find profile: {path}")
    return match.group(1)


def profile_title(profile: str) -> str:
    if SRGB_PROFILE.exists():
        try:
            if profile == profile_by_filename(SRGB_PROFILE):
                return f"sRGB ({SRGB_PROFILE})"
        except SystemExit:
            pass

    try:
        output = run("colormgr", "find-profile", profile)
    except SystemExit:
        return profile
    title = re.search(r"Title:\s*(.+)", output)
    filename = re.search(r"Filename:\s*(.+)", output)
    if title and filename:
        return f"{title.group(1).strip()} ({filename.group(1).strip()})"
    if title:
        return title.group(1).strip()
    return profile


def default_profile(device: str, *, exit_on_error: bool = True) -> str:
    try:
        output = run("colormgr", "device-get-default-profile", device)
    except SystemExit:
        if exit_on_error:
            raise
        return ""
    match = re.search(r"Object Path:\s*(\S+)", output)
    return match.group(1) if match else ""


def set_profile(device: str, profile: str) -> None:
    run_allowing("has already been added", "colormgr", "device-add-profile", device, profile)
    run("colormgr", "device-make-profile-default", device, profile)


def assign_profile(args: argparse.Namespace) -> None:
    profile = import_profile(args.profile)
    set_profile(args.device, profile)
    print(f"assigned {profile_title(profile)} to {args.device}")


def target_devices() -> tuple[list[dict[str, object]], list[str]]:
    devices = parse_colormgr_devices()
    matched: list[dict[str, object]] = []
    missing = list(TARGET_MODELS)

    for device in devices:
        model = str(device.get("model", ""))
        for target in tuple(missing):
            if target == model:
                matched.append(device)
                missing.remove(target)

    return matched, missing


def apply_srgb(_: argparse.Namespace) -> None:
    if not SRGB_PROFILE.exists():
        raise SystemExit(f"sRGB profile not found: {SRGB_PROFILE}")

    profile = profile_by_filename(SRGB_PROFILE)
    devices, missing = target_devices()

    if missing:
        print("Missing expected displays: " + ", ".join(missing), file=sys.stderr)

    if not devices:
        raise SystemExit("No target displays found in colord")

    for device in devices:
        device_id = str(device.get("device_id"))
        model = str(device.get("model", "unknown model"))
        vendor = str(device.get("vendor", "unknown vendor"))
        xrandr = str(device.get("metadata_xrandr_name", "unknown output"))
        before = default_profile(device_id, exit_on_error=False)
        set_profile(device_id, profile)
        after = default_profile(device_id)
        before_title = profile_title(before) if before else "none"
        print(f"{vendor} {model} ({xrandr})")
        print(f"  before: {before_title}")
        print(f"  after:  {profile_title(after)}")


def open_settings(_: argparse.Namespace) -> None:
    subprocess.Popen(["gnome-control-center", "color"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and assign GNOME/colord monitor ICC profiles."
    )
    subparsers = parser.add_subparsers(required=False)

    list_parser = subparsers.add_parser("list", help="show connected outputs and colord IDs")
    list_parser.set_defaults(func=list_state)

    assign_parser = subparsers.add_parser("assign", help="import and set an ICC profile")
    assign_parser.add_argument("device", help="colord device id or object path")
    assign_parser.add_argument("profile", type=Path, help="path to .icc or .icm profile")
    assign_parser.set_defaults(func=assign_profile)

    srgb_parser = subparsers.add_parser(
        "apply-srgb",
        help="set the Dell S2725QS and BenQ EL2870U to the standard sRGB ICC profile",
    )
    srgb_parser.set_defaults(func=apply_srgb)

    settings_parser = subparsers.add_parser("settings", help="open GNOME Color settings")
    settings_parser.set_defaults(func=open_settings)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        args.func = list_state
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
