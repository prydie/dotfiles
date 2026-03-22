"""Shared router API client for local Sagemcom/YouFibre tooling."""

from .client import (
    RouterClient,
    RouterFirewallRule,
    RouterIPv6PinHoleRule,
    RouterLoginChallenge,
    RouterLoginPayload,
    RouterSettings,
    build_login_payload,
    hash_password_for_router,
    load_config,
    resolve_router_settings,
)

__all__ = [
    "RouterClient",
    "RouterFirewallRule",
    "RouterIPv6PinHoleRule",
    "RouterLoginChallenge",
    "RouterLoginPayload",
    "RouterSettings",
    "build_login_payload",
    "hash_password_for_router",
    "load_config",
    "resolve_router_settings",
]
