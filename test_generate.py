from fnmatch import fnmatchcase
from ipaddress import ip_address, ip_network
from pathlib import Path
import unittest

import generate

SAMPLE = """# upstream example
[General]
dns-server = system
[Rule]
DOMAIN-SUFFIX,cn,proxy
GEOIP,CN,proxy
FINAL,DIRECT
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

    def test_upstream_cn_suffix_and_china_ip_policy(self):
        self.assertEqual(route(self.config, "example.cn", "US"), "PROXY")
        for host in ("baidu.com", "bilibili.com", "qq.com", "taobao.com", "jd.com", "223.5.5.5"):
            with self.subTest(host=host):
                self.assertEqual(route(self.config, host, "CN"), "PROXY")

    def test_upstream_does_not_invent_additional_china_domain_lists(self):
        # No extra China domains are added beyond those supplied by the upstream.
        sample_config = generate.render(SAMPLE, "test-revision", {"doubao.com"})
        self.assertEqual(route(sample_config, "bilibili.com", "US"), "DIRECT")
        for host in ("google.com", "youtube.com", "github.com", "api.openai.com", "example.hk", "example.tw", "example.cn.example.org", "doubao.com.example.org"):
            with self.subTest(host=host):
                self.assertEqual(route(self.config, host, "US"), "DIRECT")

    def test_lan_stays_direct(self):
        for host in ("localhost", "printer.local", "router.lan", "192.168.1.1", "10.0.0.1"):
            self.assertEqual(route(self.config, host, "CN"), "DIRECT")

    def test_new_upstream_rules_are_preserved(self):
        changed = SAMPLE.replace("GEOIP,CN,proxy", "DOMAIN-SUFFIX,new-upstream.example,proxy\nGEOIP,CN,proxy")
        config = generate.render(changed, "test-revision", {"doubao.com"})
        self.assertIn("DOMAIN-SUFFIX,new-upstream.example,PROXY", config)
        self.assertEqual(route(config, "new-upstream.example", "US"), "PROXY")

    def test_updated_source_still_cannot_override_doubao_direct(self):
        changed = SAMPLE.replace("GEOIP,CN,proxy", "DOMAIN-SUFFIX,doubao.com,proxy\nGEOIP,CN,proxy")
        config = generate.render(changed, "test-revision", {"doubao.com"})
        self.assertEqual(route(config, "shurufa.doubao.com", "CN"), "DIRECT")

    def test_wrong_upstream_direction_and_unknown_policy_stop_generation(self):
        for changed in (SAMPLE.replace("FINAL,DIRECT", "FINAL,PROXY"), SAMPLE.replace("GEOIP,CN,proxy", "GEOIP,CN,DIRECT"), SAMPLE.replace("DOMAIN-SUFFIX,cn,proxy", "DOMAIN-SUFFIX,cn,REJECT")):
            with self.subTest(source=changed), self.assertRaises(ValueError):
                generate.render(changed, "test-revision", set())

    def test_update_url_source_attribution_and_no_mitm(self):
        self.assertIn("update-url = " + generate.UPDATE_URL, self.config)
        self.assertIn(generate.SOURCE_REPOSITORY, self.config)
        self.assertIn("CC BY-SA 4.0", self.config)
        self.assertNotIn("v2fly", self.config)
        self.assertNotIn("[MITM]", self.config)
        self.assertNotIn("[URL Rewrite]", self.config)
        self.assertTrue(self.config.rstrip().endswith("FINAL,DIRECT"))


if __name__ == "__main__":
    unittest.main()
