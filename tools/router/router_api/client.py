"""Shared router API client for local Sagemcom/YouFibre tooling."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import http.cookiejar
import json
import os
import random
import ssl
import time
import tomllib
import urllib.parse
import urllib.request

try:
    from passlib.hash import sha512_crypt
except ImportError:  # pragma: no cover
    sha512_crypt = None


@dataclass(frozen=True)
class RouterSettings:
    router_url: str
    username: str
    password: str


@dataclass(frozen=True)
class RouterLoginChallenge:
    """Challenge cookies returned by the router before login."""

    salt: str
    nonce: str


@dataclass(frozen=True)
class RouterLoginPayload:
    """Form fields expected by `/api/v1/login`."""

    username: str
    auth_key: str
    cnonce: str


@dataclass(frozen=True)
class RouterIPv6PinHoleRule:
    """Normalized IPv6 pinhole rule for the router's firewall API."""

    name: str
    mac_address: str
    local_port: str
    protocol: str = "tcp"
    remote_ip: str = ""
    remote_port: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class RouterFirewallRule:
    """Generic firewall rule payload accepted by `/api/v2/firewall/chain/rules`."""

    description: str = ""
    action: str = "accept"
    protocol: str = ""
    enabled: bool = True
    source_ip: str = ""
    source_ports: str = ""
    dest_ip: str = ""
    dest_ports: str = ""
    source_interface: str = ""
    dest_interface: str = ""
    ip_protocol: str = ""
    mac_id: str = ""
    service_name: str = ""
    order: int | None = None


def load_config(path: str) -> dict:
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return {}
    with open(expanded, "rb") as handle:
        return tomllib.load(handle)


def _first_non_empty(*values: str) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def resolve_router_settings(
    *,
    config_path: str,
    router_url: str,
    username: str,
    password: str,
    default_router_url: str,
    url_env_vars: tuple[str, ...] = (),
    username_env_vars: tuple[str, ...] = (),
    password_env_vars: tuple[str, ...] = (),
    config_section: str = "router",
) -> RouterSettings:
    """Resolve router connection settings from args, env, and local config."""
    config = load_config(config_path)
    router_cfg = config.get(config_section, {})

    resolved_router_url = _first_non_empty(
        router_url,
        *(os.environ.get(name, "") for name in url_env_vars),
        router_cfg.get("url", ""),
        default_router_url,
    ).rstrip("/")
    resolved_username = _first_non_empty(
        username,
        *(os.environ.get(name, "") for name in username_env_vars),
        router_cfg.get("username", ""),
    )

    password_sources = [password]
    password_sources.extend(os.environ.get(name, "") for name in password_env_vars)
    password_sources.append(str(router_cfg.get("password", "")))
    resolved_password = next((value for value in password_sources if value), "")
    password_env = str(router_cfg.get("password_env", "")).strip()
    if not resolved_password and password_env:
        resolved_password = os.environ.get(password_env, "")

    return RouterSettings(
        router_url=resolved_router_url,
        username=resolved_username,
        password=resolved_password,
    )


def build_opener(
    verify_tls: bool, cookie_jar: http.cookiejar.CookieJar
) -> urllib.request.OpenerDirector:
    context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
        urllib.request.HTTPCookieProcessor(cookie_jar),
    )


def hash_password_for_router(password: str, salt: str) -> str:
    """Reproduce the router UI's SHA512-crypt password hashing step."""
    if sha512_crypt is not None:
        return sha512_crypt.using(rounds=5000, salt=salt).hash(password)

    import crypt  # pragma: no cover

    return crypt.crypt(password, f"$6${salt}$")


def build_login_payload(username: str, password: str, challenge: RouterLoginChallenge) -> RouterLoginPayload:
    """Build the challenge-response login payload used by the router web UI."""
    password_hash = hash_password_for_router(password, challenge.salt)
    if not password_hash.startswith("$6$"):
        raise RuntimeError("Router returned an unsupported login challenge")

    session_key = hashlib.sha512(
        f"{username}:{challenge.nonce}:{password_hash[3:]}".encode("utf-8")
    ).hexdigest()
    cnonce = f"{random.SystemRandom().randrange(10**19):019d}"
    auth_key = hashlib.sha512(f"{session_key}:0:{cnonce}".encode("utf-8")).hexdigest()
    return RouterLoginPayload(username=username, auth_key=auth_key, cnonce=cnonce)


class RouterClient:
    """Stateful router API client that keeps cookies in memory only."""

    FIREWALL_CHAIN_CUSTOM = "Custom"
    FIREWALL_CHAIN_PINHOLE = "PinHole"

    def __init__(self, base_url: str, verify_tls: bool, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = build_opener(verify_tls, self.cookie_jar)
        self._logged_in_at = 0.0

    def _request(self, path: str, *, method: str = "GET", data: bytes | None = None):
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        csrf_token = self._cookie("__Host-csrf_token")
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token
        request = urllib.request.Request(
            url=f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        return self.opener.open(request, timeout=self.timeout)

    def _request_json(self, path: str, *, method: str = "GET", fields: dict[str, object] | None = None):
        data = None
        if fields is not None:
            normalized = {
                key: str(value)
                for key, value in fields.items()
                if value is not None
            }
            data = urllib.parse.urlencode(normalized).encode("utf-8")
        with self._request(path, method=method, data=data) as response:
            body = response.read().decode("utf-8", errors="replace")
            if not body:
                return None
            return json.loads(body)

    def _cookie(self, name: str) -> str:
        for cookie in self.cookie_jar:
            if cookie.name == name:
                return cookie.value
        return ""

    def _get_login_challenge(self, username: str) -> RouterLoginChallenge:
        preflight = urllib.parse.urlencode({"login": username}).encode("utf-8")
        with self._request("/api/v1/login-params", method="POST", data=preflight) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Router login failed with HTTP {response.status}")

        challenge = RouterLoginChallenge(
            salt=self._cookie("salt"),
            nonce=self._cookie("nonce"),
        )
        if not challenge.salt or not challenge.nonce:
            raise RuntimeError("Router login challenge did not provide salt/nonce cookies")
        return challenge

    def login(self, username: str, password: str) -> None:
        challenge = self._get_login_challenge(username)
        login_payload = build_login_payload(username, password, challenge)
        payload = urllib.parse.urlencode(
            {
                "login": login_payload.username,
                "auth_key": login_payload.auth_key,
                "cnonce": login_payload.cnonce,
            }
        ).encode("utf-8")
        with self._request("/api/v1/login", method="POST", data=payload) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Router login failed with HTTP {response.status}")
        self._logged_in_at = time.time()

    def get_json(self, path: str):
        return self._request_json(path)

    def session_age_seconds(self) -> float:
        return time.time() - self._logged_in_at

    def session_is_fresh(self, ttl_seconds: int) -> bool:
        return self.session_age_seconds() < ttl_seconds

    def list_hosts(self):
        return self.get_json("/api/v1/hosts")

    def list_dhcp_clients(self):
        return self.get_json("/api/v1/dhcp/clients")

    def list_arp(self):
        return self.get_json("/api/v1/hosts/arp_table")

    @staticmethod
    def _normalize_firewall_ports(value: str) -> str:
        if not value or value == "0" or value == "*":
            return "-1"
        return value

    @staticmethod
    def _normalize_firewall_protocol(value: str) -> str:
        protocol = str(value or "").strip().lower()
        if protocol == "both":
            return "tcp,udp"
        return protocol

    def list_firewall_chain_rules(self, chain: str):
        """Return rules for a specific firewall chain."""
        quoted_chain = urllib.parse.quote(chain, safe="")
        return self.get_json(f"/api/v2/firewall/chain?chain={quoted_chain}")

    def set_firewall_chain_enabled(self, chain: str, enabled: bool):
        """Enable or disable one firewall chain."""
        return self._request_json(
            "/api/v2/firewall/chain",
            method="PUT",
            fields={
                "chain": chain,
                "enable": "1" if enabled else "0",
            },
        )

    def add_firewall_rule(self, rule: RouterFirewallRule, *, chain: str = FIREWALL_CHAIN_CUSTOM):
        """Create one firewall rule in the given chain."""
        payload = {
            "chain": chain,
            "enable": "1" if rule.enabled else "0",
            "action": rule.action,
            "description": rule.description,
            "protocol": self._normalize_firewall_protocol(rule.protocol) if rule.protocol else None,
            "dst_ip": rule.dest_ip or None,
            "dst_ports": self._normalize_firewall_ports(rule.dest_ports),
            "src_ip": rule.source_ip or None,
            "src_ports": self._normalize_firewall_ports(rule.source_ports),
            "src_intf": rule.source_interface or None,
            "dst_intf": rule.dest_interface or None,
            "ip_protocol": rule.ip_protocol.lower() if rule.ip_protocol else None,
            "mac_id": rule.mac_id or None,
            "service": rule.service_name or None,
            "order": str(rule.order) if rule.order is not None else None,
        }
        return self._request_json("/api/v2/firewall/chain/rules", method="POST", fields=payload)

    def edit_firewall_rule(self, rule_id: str | int, *, chain: str = FIREWALL_CHAIN_CUSTOM, **updates):
        """Update selected fields on one firewall rule."""
        payload = {"chain": chain}
        field_map = {
            "description": "description",
            "action": "action",
            "protocol": "protocol",
            "enabled": "enable",
            "source_ip": "src_ip",
            "source_ports": "src_ports",
            "dest_ip": "dst_ip",
            "dest_ports": "dst_ports",
            "source_interface": "src_intf",
            "dest_interface": "dst_intf",
            "ip_protocol": "ip_protocol",
            "mac_id": "mac_id",
            "service_name": "service",
            "order": "order",
        }
        for key, api_key in field_map.items():
            if key not in updates:
                continue
            value = updates[key]
            if key == "enabled":
                payload[api_key] = "1" if value else "0"
            elif key in {"source_ports", "dest_ports"}:
                payload[api_key] = self._normalize_firewall_ports(str(value or ""))
            elif key in {"protocol", "ip_protocol"}:
                normalized = (
                    self._normalize_firewall_protocol(str(value))
                    if key == "protocol"
                    else str(value).lower()
                )
                payload[api_key] = normalized
            elif value is not None:
                payload[api_key] = str(value)
        return self._request_json(
            f"/api/v2/firewall/chain/rules/{rule_id}",
            method="PUT",
            fields=payload,
        )

    def remove_firewall_rule(self, rule_id: str | int, *, chain: str = FIREWALL_CHAIN_CUSTOM):
        """Delete one firewall rule from the given chain."""
        return self._request_json(
            f"/api/v2/firewall/chain/rules/{rule_id}",
            method="DELETE",
            fields={"chain": chain},
        )

    def list_ipv6_pinhole_rules(self):
        """Return the current IPv6 pinhole rules from the firewall PinHole chain."""
        return self.list_firewall_chain_rules(self.FIREWALL_CHAIN_PINHOLE)

    def add_ipv6_pinhole_rule(self, rule: RouterIPv6PinHoleRule):
        """Create an IPv6 pinhole rule via the shared firewall rules API.

        The router UI's `ipv6-pin-holing` page posts to the generic
        `/api/v2/firewall/chain/rules` endpoint with `chain=PinHole`.
        """
        protocol = str(rule.protocol or "").strip().lower()
        protocols = ("tcp", "udp") if protocol in {"both", "tcp,udp"} else (protocol,)
        results = []
        for current_protocol in protocols:
            firewall_rule = RouterFirewallRule(
                description=rule.name,
                action="Accept",
                protocol=current_protocol,
                enabled=rule.enabled,
                source_ip=rule.remote_ip,
                source_ports=rule.remote_port,
                dest_ports=rule.local_port,
                source_interface="wan",
                dest_interface="lan",
                ip_protocol="ipv6",
                mac_id=rule.mac_address,
            )
            results.append(self.add_firewall_rule(firewall_rule, chain=self.FIREWALL_CHAIN_PINHOLE))
        return results[0] if len(results) == 1 else results

    def remove_ipv6_pinhole_rule(self, rule_id: str | int):
        """Delete one IPv6 pinhole rule from the firewall PinHole chain."""
        return self.remove_firewall_rule(rule_id, chain=self.FIREWALL_CHAIN_PINHOLE)
