from fnmatch import fnmatchcase
from ipaddress import ip_address, ip_network
from pathlib import Path
import unittest

import generate

SAMPLE = """# upstream sr_cnip example
[General]
dns-server = system
[Rule]
DOMAIN-SUFFIX,bing.com,proxy
DOMAIN-SUFFIX,github.com,Proxy
IP-CIDR,91.108.56.0/22,Proxy
GEOIP,CN,DIRECT
FINAL,proxy
[MITM]
hostname = example.cn
"""


def route(config, host, region):
    host = host.encode("idna").decode().lower().rstrip(".")
    for line in config.split("[Rule]\n", 1)[1].splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split(",")
        kind = fields[0]
        if kind == "FINAL":
            return fields[1]
        value, policy = fields[1:3]
        if kind == "DOMAIN" and host == value:
            return policy
        if kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value)):
            return policy
        if kind == "DOMAIN-KEYWORD" and value in host:
            return policy
        if kind == "DOMAIN-WILDCARD" and fnmatchcase(host, value):
            return policy
        if kind == "GEOIP" and region == value:
            return policy
        if kind in {"IP-CIDR", "IP-CIDR6"}:
            try:
                address = ip_address(host)
            except ValueError:
                continue
            network = ip_network(value)
            if address.version == network.version and address in network:
                return policy
    raise AssertionError("No final rule")


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = (Path(__file__).parent / "sr_china_proxy.conf").read_text()

    def test_doubao_is_direct_even_for_china_destination_ips(self):
        for host in ("doubao.com", "www.doubao.com", "shurufa.doubao.com", "doubaoapps.com", "cdn.doubaocdn.com", "doubao-dev.com", "openspeech.bytedance.com"):
            with self.subTest(host=host):
                self.assertEqual(route(self.config, host, "CN"), "DIRECT")

    def test_china_ip_always_proxies_even_for_original_foreign_overrides(self):
        for host in ("baidu.com", "bilibili.com", "bing.com", "github.com", "linkedin.cn", "223.5.5.5"):
            with self.subTest(host=host):
                self.assertEqual(route(self.config, host, "CN"), "PROXY")

    def test_non_china_ip_is_direct_even_for_cn_domain(self):
        for host in ("example.cn", "bilibili.com", "google.com", "bing.com", "github.com", "api.openai.com", "example.hk", "example.tw", "example.cn.example.org", "doubao.com.example.org", "91.108.56.1"):
            with self.subTest(host=host):
                self.assertEqual(route(self.config, host, "US"), "DIRECT")
        self.assertNotIn("DOMAIN-SUFFIX,cn,PROXY", self.config)

    def test_lan_stays_direct(self):
        for host in ("localhost", "printer.local", "router.lan", "192.168.1.1", "10.0.0.1"):
            self.assertEqual(route(self.config, host, "CN"), "DIRECT")

    def test_upstream_conversion_preserves_entries_as_direct_after_geoip(self):
        rules = generate.upstream_rules(SAMPLE)
        self.assertEqual(rules, [
            "GEOIP,CN,PROXY", "DOMAIN-SUFFIX,bing.com,DIRECT",
            "DOMAIN-SUFFIX,github.com,DIRECT", "IP-CIDR,91.108.56.0/22,DIRECT", "FINAL,DIRECT",
        ])
        changed = SAMPLE.replace("GEOIP,CN,DIRECT", "DOMAIN-SUFFIX,new-upstream.example,proxy\nGEOIP,CN,DIRECT")
        config = generate.render(changed, "test-revision", {"doubao.com"})
        self.assertIn("DOMAIN-SUFFIX,new-upstream.example,DIRECT", config)
        self.assertEqual(route(config, "new-upstream.example", "US"), "DIRECT")
        self.assertEqual(route(config, "new-upstream.example", "CN"), "PROXY")

    def test_updated_source_cannot_override_doubao_direct(self):
        changed = SAMPLE.replace("GEOIP,CN,DIRECT", "DOMAIN-SUFFIX,doubao.com,proxy\nGEOIP,CN,DIRECT")
        config = generate.render(changed, "test-revision", {"doubao.com"})
        self.assertEqual(route(config, "shurufa.doubao.com", "CN"), "DIRECT")

    def test_wrong_source_direction_and_unknown_policy_stop_generation(self):
        for changed in (SAMPLE.replace("FINAL,proxy", "FINAL,DIRECT"), SAMPLE.replace("GEOIP,CN,DIRECT", "GEOIP,CN,PROXY"), SAMPLE.replace("DOMAIN-SUFFIX,bing.com,proxy", "DOMAIN-SUFFIX,bing.com,REJECT")):
            with self.subTest(source=changed), self.assertRaises(ValueError):
                generate.render(changed, "test-revision", set())

    def test_fixed_source_update_url_and_only_cn_geoip_can_proxy(self):
        self.assertEqual(generate.SOURCE_FILE, "sr_cnip.conf")
        self.assertIn("update-url = " + generate.UPDATE_URL, self.config)
        self.assertIn("/sr_cnip.conf", self.config)
        self.assertIn("CC BY-SA 4.0", self.config)
        self.assertNotIn("sr_backcn.conf", self.config)
        self.assertNotIn("v2fly", self.config)
        self.assertNotIn("[MITM]", self.config)
        self.assertNotIn("[URL Rewrite]", self.config)
        proxy_rules = [line for line in self.config.splitlines() if not line.startswith("#") and ",PROXY" in line]
        self.assertEqual(proxy_rules, ["GEOIP,CN,PROXY"])
        self.assertTrue(self.config.rstrip().endswith("FINAL,DIRECT"))


if __name__ == "__main__":
    unittest.main()
