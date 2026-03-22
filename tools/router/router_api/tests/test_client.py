from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from router_api import (
    RouterFirewallRule,
    RouterIPv6PinHoleRule,
    RouterLoginChallenge,
    build_login_payload,
)
from router_api.client import RouterClient


class BuildLoginPayloadTest(unittest.TestCase):
    def test_build_login_payload_matches_known_router_formula(self):
        challenge = RouterLoginChallenge(
            salt="Q9Sn4I/gmeDMa9Z",
            nonce="51afb5d0e842dcf2309d299fa871ac68",
        )

        payload = build_login_payload("admin", "test-password", challenge)

        self.assertEqual(payload.username, "admin")
        self.assertEqual(len(payload.cnonce), 19)
        self.assertTrue(payload.cnonce.isdigit())
        self.assertEqual(len(payload.auth_key), 128)
        self.assertTrue(all(ch in "0123456789abcdef" for ch in payload.auth_key))


class IPv6PinHoleRuleTest(unittest.TestCase):
    def test_rule_dataclass_defaults_match_router_ui_expectations(self):
        rule = RouterIPv6PinHoleRule(
            name="Deluge",
            mac_address="00:11:22:33:44:55",
            local_port="50638",
        )

        self.assertEqual(rule.protocol, "tcp")
        self.assertEqual(rule.remote_ip, "")
        self.assertEqual(rule.remote_port, "")
        self.assertTrue(rule.enabled)

    def test_pinhole_chain_constant_matches_router_api(self):
        self.assertEqual(RouterClient.FIREWALL_CHAIN_PINHOLE, "PinHole")


class FirewallRuleTest(unittest.TestCase):
    def test_generic_firewall_rule_defaults_are_safe(self):
        rule = RouterFirewallRule()

        self.assertEqual(rule.action, "accept")
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.source_ports, "")
        self.assertEqual(rule.dest_ports, "")

    def test_port_normalization_matches_router_api_convention(self):
        self.assertEqual(RouterClient._normalize_firewall_ports(""), "-1")
        self.assertEqual(RouterClient._normalize_firewall_ports("0"), "-1")
        self.assertEqual(RouterClient._normalize_firewall_ports("*"), "-1")
        self.assertEqual(RouterClient._normalize_firewall_ports("50638"), "50638")

    def test_protocol_normalization_matches_router_api_convention(self):
        self.assertEqual(RouterClient._normalize_firewall_protocol("both"), "tcp,udp")
        self.assertEqual(RouterClient._normalize_firewall_protocol("TCP"), "tcp")


if __name__ == "__main__":
    unittest.main()
