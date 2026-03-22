#!/usr/bin/env python3

import argparse
import getpass
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import urllib.error
from dataclasses import asdict, dataclass

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from router_api import RouterClient, resolve_router_settings


DEFAULT_CONFIG_PATH = os.path.expanduser(
    os.environ.get("LAN_DISCOVER_CONFIG", "~/.config/lan-discover/config.toml")
)
DEFAULT_ROUTER_URL = os.environ.get("LAN_DISCOVER_ROUTER_URL", "https://192.168.1.1")
DEFAULT_VERIFY_TLS = os.environ.get("LAN_DISCOVER_VERIFY_TLS", "0") == "1"


@dataclass
class Device:
    ip: str
    mac: str
    reserved_ip: str = ""
    hostname: str = ""
    friendly_name: str = ""
    active: bool = False
    link: str = ""
    interface: str = ""
    lease_seconds: int = 0
    device_type: str = ""
    source: str = ""
    reservation: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List LAN devices from a Sagemcom-based router without scanning the network."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Local config file path (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--router-url",
        default="",
        help=f"Router base URL (default: {DEFAULT_ROUTER_URL} or config file)",
    )
    parser.add_argument(
        "--username",
        default="",
        help="Router username (or set LAN_DISCOVER_ROUTER_USER / config file).",
    )
    parser.add_argument(
        "--password",
        default="",
        help="Router password (or set LAN_DISCOVER_ROUTER_PASSWORD / config file).",
    )
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        default=DEFAULT_VERIFY_TLS,
        help="Verify the router TLS certificate. Disabled by default for local self-signed certs.",
    )
    parser.add_argument(
        "--include-arp",
        action="store_true",
        help="Also query /api/v1/hosts/arp_table and merge any extra MAC/IP rows.",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Show only currently active devices.",
    )
    parser.add_argument(
        "--name",
        default="",
        help="Case-insensitive partial match against hostname or friendly name.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a table.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds (default: 15.0).",
    )
    return parser.parse_args()


def resolve_settings(args: argparse.Namespace) -> tuple[str, str, str]:
    settings = resolve_router_settings(
        config_path=args.config,
        router_url=args.router_url,
        username=args.username,
        password=args.password,
        default_router_url=DEFAULT_ROUTER_URL,
        url_env_vars=("LAN_DISCOVER_ROUTER_URL",),
        username_env_vars=("LAN_DISCOVER_ROUTER_USER",),
        password_env_vars=("LAN_DISCOVER_ROUTER_PASSWORD",),
    )
    return settings.router_url, settings.username, settings.password


def to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_hosts(payload) -> dict[str, Device]:
    devices: dict[str, Device] = {}
    rows = payload[0].get("hosts", {}).get("list", []) if payload else []
    for row in rows:
        ip = str(row.get("ipaddress", "")).strip()
        mac = str(row.get("macaddress", "")).strip().lower()
        if not ip and not mac:
            continue
        key = mac or ip
        devices[key] = Device(
            ip=ip,
            mac=mac,
            hostname=str(row.get("hostname", "")).strip(),
            friendly_name=str(row.get("friendlyHostname", "")).strip(),
            active=to_bool(row.get("active", False)),
            link=str(row.get("link", "")).strip(),
            interface=str(row.get("interface_l3", "")).strip()
            or str(row.get("Layer1Interface", "")).strip(),
            lease_seconds=to_int(row.get("lease")),
            device_type=str(row.get("devicetype", "")).strip(),
            source="hosts",
        )
    return devices


def normalize_dhcp_clients(payload) -> dict[str, Device]:
    devices: dict[str, Device] = {}
    rows = payload[0].get("dhcp", {}).get("clients", []) if payload else []
    for row in rows:
        ip = str(row.get("ipaddress", "")).strip()
        mac = str(row.get("macaddress", "")).strip().lower()
        if not ip and not mac:
            continue
        key = mac or ip
        devices[key] = Device(
            ip="",
            mac=mac,
            reserved_ip=ip,
            hostname=str(row.get("hostname", "")).strip(),
            active=to_bool(row.get("enable", False)),
            source="dhcp",
            reservation=True,
        )
    return devices


def normalize_arp(payload) -> dict[str, Device]:
    devices: dict[str, Device] = {}
    if not payload:
        return devices

    rows = []
    first = payload[0]
    if isinstance(first, dict):
        if "hosts" in first and isinstance(first["hosts"], dict):
            rows = first["hosts"].get("arp_table", []) or first["hosts"].get("list", [])
        elif "arp_table" in first:
            rows = first.get("arp_table", [])

    for row in rows:
        if not isinstance(row, dict):
            continue
        ip = str(row.get("ipaddress", "") or row.get("ip", "")).strip()
        mac = str(row.get("macaddress", "") or row.get("mac", "")).strip().lower()
        if not ip and not mac:
            continue
        key = mac or ip
        devices[key] = Device(
            ip=ip,
            mac=mac,
            interface=str(row.get("interface_l3", "") or row.get("interface", "")).strip(),
            source="arp",
        )
    return devices


def merge_devices(*maps: dict[str, Device]) -> list[Device]:
    merged: dict[str, Device] = {}

    for device_map in maps:
        for key, incoming in device_map.items():
            current = merged.get(key)
            if current is None:
                merged[key] = Device(**asdict(incoming))
                continue

            if not current.ip and incoming.ip:
                current.ip = incoming.ip
            if not current.mac and incoming.mac:
                current.mac = incoming.mac
            if not current.reserved_ip and incoming.reserved_ip:
                current.reserved_ip = incoming.reserved_ip
            if not current.hostname and incoming.hostname:
                current.hostname = incoming.hostname
            if not current.friendly_name and incoming.friendly_name:
                current.friendly_name = incoming.friendly_name
            current.active = current.active or incoming.active
            if not current.link and incoming.link:
                current.link = incoming.link
            if not current.interface and incoming.interface:
                current.interface = incoming.interface
            current.lease_seconds = max(current.lease_seconds, incoming.lease_seconds)
            if not current.device_type and incoming.device_type:
                current.device_type = incoming.device_type
            current.reservation = current.reservation or incoming.reservation

            sources = [part for part in current.source.split(",") if part]
            if incoming.source and incoming.source not in sources:
                sources.append(incoming.source)
                current.source = ",".join(sources)

    return sorted(merged.values(), key=device_sort_key)


def device_sort_key(item: Device) -> tuple[int, int, bytes, str]:
    if not item.ip:
        return (2, 0, b"", "")

    try:
        parsed = ipaddress.ip_address(item.ip)
    except ValueError:
        return (3, 0, b"", item.ip)

    family_rank = 0 if parsed.version == 4 else 1
    return (family_rank, int(parsed), parsed.packed, item.ip)


def render_table(devices: list[Device]) -> None:
    columns = [
        ("IP", "ip"),
        ("ReservedIP", "reserved_ip"),
        ("MAC", "mac"),
        ("Name", "hostname"),
        ("Friendly", "friendly_name"),
        ("Active", "active"),
        ("Link", "link"),
        ("Iface", "interface"),
        ("Lease", "lease_seconds"),
        ("Reserved", "reservation"),
        ("Source", "source"),
    ]

    rows: list[dict[str, str]] = []
    for device in devices:
        rows.append(
            {
                "ip": device.ip,
                "reserved_ip": device.reserved_ip,
                "mac": device.mac,
                "hostname": device.hostname,
                "friendly_name": device.friendly_name,
                "active": "yes" if device.active else "no",
                "link": device.link,
                "interface": device.interface,
                "lease_seconds": str(device.lease_seconds),
                "reservation": "yes" if device.reservation else "no",
                "source": device.source,
            }
        )

    widths: dict[str, int] = {}
    for heading, field_name in columns:
        widths[field_name] = len(heading)
        for row in rows:
            widths[field_name] = max(widths[field_name], len(row[field_name]))

    print("  ".join(heading.ljust(widths[field_name]) for heading, field_name in columns))
    print("  ".join("-" * widths[field_name] for _, field_name in columns))
    for row in rows:
        print("  ".join(row[field_name].ljust(widths[field_name]) for _, field_name in columns))


def matches_name(device: Device, query: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True
    haystacks = [
        device.hostname.lower(),
        device.friendly_name.lower(),
    ]
    return any(needle in haystack for haystack in haystacks)


def main() -> int:
    args = parse_args()
    router_url, username, password = resolve_settings(args)

    if not username:
        print("Router username is required.", file=sys.stderr)
        return 2
    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass("Router password: ")
        else:
            print("Router password is required.", file=sys.stderr)
            return 2

    client = RouterClient(router_url, args.verify_tls, args.timeout)
    try:
        client.login(username, password)
        host_devices = normalize_hosts(client.list_hosts())
        dhcp_devices = normalize_dhcp_clients(client.list_dhcp_clients())
        arp_devices = normalize_arp(client.list_arp()) if args.include_arp else {}
    except urllib.error.HTTPError as exc:
        print(f"Router request failed: HTTP {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Unable to reach router: {exc.reason}", file=sys.stderr)
        return 1
    except socket.timeout:
        print(
            f"Router request timed out after {args.timeout:.1f}s. "
            "Try --timeout 30 or verify the router URL/TLS setting.",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    devices = merge_devices(host_devices, dhcp_devices, arp_devices)
    if args.active_only:
        devices = [device for device in devices if device.active]
    if args.name.strip():
        devices = [device for device in devices if matches_name(device, args.name)]

    if args.json:
        json.dump([asdict(device) for device in devices], sys.stdout, indent=2)
        print()
    else:
        render_table(devices)
    return 0


if __name__ == "__main__":
    sys.exit(main())
