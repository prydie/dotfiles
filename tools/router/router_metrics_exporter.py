#!/usr/bin/env python3
"""Prometheus exporter for Sagemcom/YouFibre router metrics.

The module is intentionally import-friendly:
- importing it does not touch the network or read credentials
- `RouterClient` can be reused by other tooling
- `render_metrics()` can be called directly if another entrypoint wants to expose
  the same metric set
"""

import argparse
import http.server
import logging
import os
from pathlib import Path
import socket
import socketserver
import threading
import sys
import time
import urllib.error
from typing import Iterable

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from router_api import RouterClient, resolve_router_settings


DEFAULT_CONFIG_PATH = os.path.expanduser(
    os.environ.get("ROUTER_EXPORTER_CONFIG", "~/.config/lan-discover/config.toml")
)
DEFAULT_ROUTER_URL = os.environ.get("ROUTER_EXPORTER_ROUTER_URL", "https://192.168.1.1")
DEFAULT_VERIFY_TLS = os.environ.get("ROUTER_EXPORTER_VERIFY_TLS", "0") == "1"
DEFAULT_TIMEOUT = float(os.environ.get("ROUTER_EXPORTER_TIMEOUT", "15.0"))
DEFAULT_PORT = int(os.environ.get("ROUTER_EXPORTER_PORT", "9787"))
DEFAULT_LISTEN = os.environ.get("ROUTER_EXPORTER_LISTEN", "0.0.0.0")
DEFAULT_PATH = os.environ.get("ROUTER_EXPORTER_METRICS_PATH", "/metrics")
SESSION_TTL_SECONDS = int(os.environ.get("ROUTER_EXPORTER_SESSION_TTL", "540"))
LOGIN_BACKOFF_INITIAL_SECONDS = int(os.environ.get("ROUTER_EXPORTER_LOGIN_BACKOFF_INITIAL", "60"))
LOGIN_BACKOFF_MAX_SECONDS = int(os.environ.get("ROUTER_EXPORTER_LOGIN_BACKOFF_MAX", "900"))
DEFAULT_LOG_LEVEL = os.environ.get("ROUTER_EXPORTER_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("router_metrics_exporter")


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prometheus exporter for Sagemcom/YouFibre router metrics."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--router-url", default="")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--verify-tls", action="store_true", default=DEFAULT_VERIFY_TLS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--listen", default=DEFAULT_LISTEN)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--metrics-path", default=DEFAULT_PATH)
    parser.add_argument("--log-level", default=DEFAULT_LOG_LEVEL)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Render metrics once to stdout and exit.",
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
        username_env_vars=("ROUTER_EXPORTER_USERNAME", "LAN_DISCOVER_ROUTER_USER"),
        password_env_vars=("ROUTER_EXPORTER_PASSWORD", "LAN_DISCOVER_ROUTER_PASSWORD"),
    )
    return settings.router_url, settings.username, settings.password


def metric_line(name: str, value, labels: dict[str, str] | None = None) -> str:
    if labels:
        label_parts = [f'{key}="{escape_label(val)}"' for key, val in sorted(labels.items())]
        return f"{name}{{{','.join(label_parts)}}} {value}"
    return f"{name} {value}"


def escape_label(value) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def bool_to_num(value) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "on", "up"} else 0
    return 1 if value else 0


def as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalized_label(value, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def count_by(rows, field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = normalized_label(row.get(field))
        counts[key] = counts.get(key, 0) + 1
    return counts


def render_metrics(client: RouterClient) -> str:
    """Fetch the current router state and render a Prometheus text payload."""
    wan_status = client.get_json("/api/v1/wan/status")
    wan_ip_stats = client.get_json("/api/v1/wan/ip/stats")
    lan_stats = client.get_json("/api/v1/lan/stats")
    session_count = client.get_json("/api/v1/session-count")
    network_parameters = client.get_json("/api/v1/network_parameters")
    hosts = client.get_json("/api/v1/hosts")
    dhcp_clients = client.get_json("/api/v1/dhcp/clients")

    lines: list[str] = []
    lines.extend(help_block())

    wan_row = wan_status[0] if wan_status else {}
    lines.append(metric_line("router_wan_up", bool_to_num(wan_row.get("status", "") == "Up")))
    lines.append(metric_line("router_wan_lastchange_seconds", as_int(wan_row.get("lastchange"))))

    stats_row = wan_ip_stats[0].get("wan", {}).get("ip", {}).get("stats", {}) if wan_ip_stats else {}
    for direction in ("rx", "tx"):
        stats = stats_row.get(direction, {})
        labels = {"direction": direction}
        lines.append(metric_line("router_wan_packets_total", as_int(stats.get("packets")), labels))
        lines.append(metric_line("router_wan_bytes_total", as_int(stats.get("bytes")), labels))
        lines.append(metric_line("router_wan_packet_errors_total", as_int(stats.get("packetserrors")), labels))
        lines.append(metric_line("router_wan_packet_discards_total", as_int(stats.get("packetsdiscards")), labels))

    lan_row = lan_stats[0].get("lan", {}) if lan_stats else {}
    lines.append(metric_line("router_lan_interfaces_total", len(lan_row.get("interfaces", []))))
    for iface in lan_row.get("interfaces", []):
        labels = {
            "iface": str(iface.get("name", "")).strip(),
            "alias": str(iface.get("alias", "")).strip(),
            "role": str(iface.get("role", "")).strip(),
        }
        lines.append(metric_line("router_interface_up", bool_to_num(iface.get("status", "") == "UP"), labels))
        lines.append(metric_line("router_interface_enabled", bool_to_num(iface.get("enable")), labels))
        lines.append(metric_line("router_interface_current_bitrate_mbps", as_float(iface.get("curbitrate")), labels))
        lines.append(metric_line("router_interface_eee_enabled", bool_to_num(iface.get("eee_enable")), labels))
        for direction in ("rx", "tx"):
            stats = iface.get(direction, {})
            dir_labels = dict(labels)
            dir_labels["direction"] = direction
            lines.append(metric_line("router_interface_packets_total", as_int(stats.get("packets")), dir_labels))
            lines.append(metric_line("router_interface_bytes_total", as_int(stats.get("bytes")), dir_labels))
            lines.append(
                metric_line("router_interface_packet_errors_total", as_int(stats.get("packetserrors")), dir_labels)
            )
            lines.append(
                metric_line("router_interface_packet_discards_total", as_int(stats.get("packetsdiscards")), dir_labels)
            )

    sessions_row = session_count[0] if session_count else {}
    lines.append(metric_line("router_sessions", as_int(sessions_row.get("sessions"))))

    network_row = network_parameters[0] if network_parameters else {}
    lines.append(
        metric_line(
            "router_network_info",
            1,
            {
                "mac_address": str(network_row.get("macAddress", "")).strip(),
                "default_gateway": str(network_row.get("defaultGateway", "")).strip(),
                "public_ipv4": str(network_row.get("publicIpv4", "")).strip(),
                "public_subnet_mask": str(network_row.get("publicSubnetMask", "")).strip(),
                "local_gateway_ipv6": str(network_row.get("localGatewayIpv6", "")).strip(),
                "public_ipv6": str(network_row.get("publicIpv6", "")).strip(),
                "default_gateway_ipv6": str(network_row.get("defaultGatewayIpv6", "")).strip(),
            },
        )
    )

    host_rows = hosts[0].get("hosts", {}).get("list", []) if hosts else []
    dhcp_rows = dhcp_clients[0].get("dhcp", {}).get("clients", []) if dhcp_clients else []
    active_hosts = sum(1 for row in host_rows if bool_to_num(row.get("active")))
    lines.append(metric_line("router_hosts_total", len(host_rows)))
    lines.append(metric_line("router_hosts_active", active_hosts))
    lines.append(metric_line("router_dhcp_reservations_total", len(dhcp_rows)))

    active_rows = [row for row in host_rows if bool_to_num(row.get("active"))]
    for link, count in sorted(count_by(host_rows, "link").items()):
        lines.append(metric_line("router_hosts_by_link_total", count, {"link": link}))
    for link, count in sorted(count_by(active_rows, "link").items()):
        lines.append(metric_line("router_hosts_active_by_link", count, {"link": link}))
    for host_type, count in sorted(count_by(host_rows, "type").items()):
        lines.append(metric_line("router_hosts_by_type_total", count, {"host_type": host_type}))
    for device_type, count in sorted(count_by(host_rows, "devicetype").items()):
        lines.append(
            metric_line("router_hosts_by_device_type_total", count, {"device_type": device_type})
        )

    enabled_reservations = sum(1 for row in dhcp_rows if bool_to_num(row.get("enable", True)))
    lines.append(metric_line("router_dhcp_reservations_enabled", enabled_reservations))

    return "\n".join(lines) + "\n"


def help_block() -> Iterable[str]:
    return [
        "# HELP router_wan_up WAN link state (1 for up, 0 for down).",
        "# TYPE router_wan_up gauge",
        "# HELP router_wan_lastchange_seconds Router-reported WAN last-change counter.",
        "# TYPE router_wan_lastchange_seconds gauge",
        "# HELP router_wan_packets_total WAN packets by direction.",
        "# TYPE router_wan_packets_total counter",
        "# HELP router_wan_bytes_total WAN bytes by direction.",
        "# TYPE router_wan_bytes_total counter",
        "# HELP router_wan_packet_errors_total WAN packet errors by direction.",
        "# TYPE router_wan_packet_errors_total counter",
        "# HELP router_wan_packet_discards_total WAN packet discards by direction.",
        "# TYPE router_wan_packet_discards_total counter",
        "# HELP router_lan_interfaces_total Number of LAN stats interfaces returned.",
        "# TYPE router_lan_interfaces_total gauge",
        "# HELP router_interface_up Interface status (1 for UP, 0 otherwise).",
        "# TYPE router_interface_up gauge",
        "# HELP router_interface_enabled Interface enabled state.",
        "# TYPE router_interface_enabled gauge",
        "# HELP router_interface_current_bitrate_mbps Current interface bitrate in Mbps.",
        "# TYPE router_interface_current_bitrate_mbps gauge",
        "# HELP router_interface_eee_enabled Interface EEE enabled state.",
        "# TYPE router_interface_eee_enabled gauge",
        "# HELP router_interface_packets_total Interface packets by direction.",
        "# TYPE router_interface_packets_total counter",
        "# HELP router_interface_bytes_total Interface bytes by direction.",
        "# TYPE router_interface_bytes_total counter",
        "# HELP router_interface_packet_errors_total Interface packet errors by direction.",
        "# TYPE router_interface_packet_errors_total counter",
        "# HELP router_interface_packet_discards_total Interface packet discards by direction.",
        "# TYPE router_interface_packet_discards_total counter",
        "# HELP router_sessions Active router management sessions.",
        "# TYPE router_sessions gauge",
        "# HELP router_network_info Static network identity labels with value 1.",
        "# TYPE router_network_info gauge",
        "# HELP router_hosts_total Number of hosts known to the router.",
        "# TYPE router_hosts_total gauge",
        "# HELP router_hosts_active Number of active hosts known to the router.",
        "# TYPE router_hosts_active gauge",
        "# HELP router_dhcp_reservations_total Number of DHCP reservations.",
        "# TYPE router_dhcp_reservations_total gauge",
        "# HELP router_hosts_by_link_total Known hosts grouped by router link type.",
        "# TYPE router_hosts_by_link_total gauge",
        "# HELP router_hosts_active_by_link Active hosts grouped by router link type.",
        "# TYPE router_hosts_active_by_link gauge",
        "# HELP router_hosts_by_type_total Known hosts grouped by router host type.",
        "# TYPE router_hosts_by_type_total gauge",
        "# HELP router_hosts_by_device_type_total Known hosts grouped by router device type.",
        "# TYPE router_hosts_by_device_type_total gauge",
        "# HELP router_dhcp_reservations_enabled Enabled DHCP reservations.",
        "# TYPE router_dhcp_reservations_enabled gauge",
    ]


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class ExporterState:
    """Shared server state for concurrent scrape requests.

    One request performs refresh work at a time. Other overlapping requests can
    serve the last completed payload immediately once the exporter has warmed up.
    """

    def __init__(
        self,
        *,
        router_url: str,
        username: str,
        password: str,
        verify_tls: bool,
        timeout: float,
    ):
        self.username = username
        self.password = password
        self.client = RouterClient(router_url, verify_tls, timeout)
        self.lock = threading.Lock()
        self.cache_lock = threading.Lock()
        self.last_payload: bytes | None = None
        self.login_backoff_seconds = max(1, LOGIN_BACKOFF_INITIAL_SECONDS)
        self.login_blocked_until = 0.0

    def scrape(self) -> bytes:
        if self.lock.acquire(blocking=False):
            try:
                payload = self._scrape_locked()
                with self.cache_lock:
                    self.last_payload = payload
                return payload
            finally:
                self.lock.release()

        with self.cache_lock:
            payload = self.last_payload
        if payload is not None:
            return payload

        # Cold start: wait for the in-flight refresh so we can return the first complete snapshot.
        with self.lock:
            with self.cache_lock:
                payload = self.last_payload
            if payload is not None:
                return payload

            payload = self._scrape_locked()
            with self.cache_lock:
                self.last_payload = payload
            return payload

    def _login_locked(self, reason: str) -> None:
        # The router rate-limits login attempts aggressively once unhappy. We keep
        # scrape failures visible, but we stop retrying logins on every 15s scrape.
        now = time.time()
        if now < self.login_blocked_until:
            remaining = max(1, int(self.login_blocked_until - now))
            raise RuntimeError(f"Router login backoff active for {remaining}s after rate limiting")

        try:
            self.client.login(self.username, self.password)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise

            delay = self.login_backoff_seconds
            self.login_blocked_until = time.time() + delay
            self.login_backoff_seconds = min(LOGIN_BACKOFF_MAX_SECONDS, delay * 2)
            logger.warning(
                "login rate-limited during %s; backing off for %ss",
                reason,
                delay,
            )
            raise RuntimeError(f"Router login rate-limited (429); backing off for {delay}s") from exc
        else:
            self.login_backoff_seconds = max(1, LOGIN_BACKOFF_INITIAL_SECONDS)
            self.login_blocked_until = 0.0

    def _scrape_locked(self) -> bytes:
        if not self.client.session_is_fresh(SESSION_TTL_SECONDS):
            logger.info("refreshing router session")
            self._login_locked("session refresh")
        try:
            return render_metrics(self.client).encode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code not in (400, 401, 403):
                raise
        except urllib.error.URLError:
            raise
        except Exception:
            raise

        # The router session can expire server-side before our local TTL. Refresh once and retry.
        logger.info("retrying scrape after auth error")
        self._login_locked("auth retry")
        return render_metrics(self.client).encode("utf-8")


def make_handler(
    *,
    state: ExporterState,
    metrics_path: str,
):
    class MetricsHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path != metrics_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"not found\n")
                return

            try:
                payload = state.scrape()
            except Exception as exc:  # pragma: no cover
                logger.exception("scrape failed: %s", exc)
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"scrape failed: {exc}\n".encode("utf-8", errors="replace"))
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args):  # noqa: A003
            return

    return MetricsHandler


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)
    router_url, username, password = resolve_settings(args)

    if not username:
        logger.error("Router username is required.")
        return 2
    if not password:
        logger.error("Router password is required.")
        return 2

    if args.once:
        client = RouterClient(router_url, args.verify_tls, args.timeout)
        try:
            client.login(username, password)
            sys.stdout.write(render_metrics(client))
        except socket.timeout:
            logger.error(
                "Router request timed out after %.1fs. Try --timeout 30 or verify the router URL/TLS setting.",
                args.timeout,
            )
            return 1
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, ValueError) as exc:
            logger.error("%s", exc)
            return 1
        return 0

    state = ExporterState(
        router_url=router_url,
        username=username,
        password=password,
        verify_tls=args.verify_tls,
        timeout=args.timeout,
    )
    server = ThreadingHTTPServer(
        (args.listen, args.port),
        make_handler(
            state=state,
            metrics_path=args.metrics_path,
        ),
    )
    logger.info(
        "listening on http://%s:%s%s",
        args.listen,
        args.port,
        args.metrics_path,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
