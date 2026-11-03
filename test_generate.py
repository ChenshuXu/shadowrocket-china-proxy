import fnmatch
from pathlib import Path
import unittest

import generate


def domain_policy(host):
    host = host.encode("idna").decode().lower().rstrip(".")
    for line in (Path(__file__).parent / "sr_china_proxy.conf").read_text().splitlines():
        if not line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,", "DOMAIN-WILDCARD,")):
            continue
        kind, value, policy = line.split(",")
        if kind == "DOMAIN" and host == value:
            return policy
        if kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value)):
            return policy
        if kind == "DOMAIN-WILDCARD" and fnmatch.fnmatchcase(host, value):
            return policy
    return "GEOIP"


class RoutingTests(unittest.TestCase):
    def test_doubao_overrides_china_domains_and_ip_fallback(self):
        for host in ("doubao.com", "www.doubao.com", "shurufa.doubao.com", "doubaoapps.com", "cdn.doubaocdn.com", "doubao-dev.com", "openspeech.bytedance.com"):
            with self.subTest(host=host):
                self.assertEqual(domain_policy(host), "DIRECT")

    def test_other_chinese_sites_still_proxy(self):
        for host in ("www.baidu.com", "www.bilibili.com", "i0.hdslb.com", "qq.com", "v.qq.com", "taobao.com", "jd.com", "163.com", "zhihu.com", "xiaohongshu.com", "douyin.com", "example.cn", "example.中国", "asset-mihayo.akamaized.net", "ns.awsdns-cn-09.com"):
            with self.subTest(host=host):
                self.assertEqual(domain_policy(host), "PROXY")

    def test_foreign_and_lookalike_domains_reach_ip_fallback(self):
        for host in ("google.com", "youtube.com", "github.com", "api.openai.com", "apple.com", "microsoft.com", "netflix.com", "amazon.com", "tiktok.com", "stripe.com", "akamai.com", "cloudflare.com", "example.hk", "example.tw", "baidu.com.example.org", "doubao.com.example.org", "notdoubao.com"):
            with self.subTest(host=host):
                self.assertEqual(domain_policy(host), "GEOIP")

    def test_update_url_and_last_rules(self):
        config = (Path(__file__).parent / "sr_china_proxy.conf").read_text()
        self.assertIn("update-url = " + generate.UPDATE_URL, config)
        rules = [line for line in config.split("[Rule]\n", 1)[1].splitlines() if line and not line.startswith("#")]
        self.assertEqual(rules[-2:], ["GEOIP,CN,PROXY", "FINAL,DIRECT"])
        self.assertLess(rules.index("DOMAIN-SUFFIX,openspeech.bytedance.com,DIRECT"), rules.index("DOMAIN-SUFFIX,bytedance.com,PROXY"))

    def test_include_filters_preserve_untagged_and_remove_overseas(self):
        files = {"cn": "include:vendor @-!cn", "vendor": "domestic.example\noverseas.example @!cn\nfull:exact.example @ads"}
        self.assertEqual(generate.expand_cn(files), {("domain", "domestic.example"), ("full", "exact.example")})

    def test_unknown_regex_stops_generation(self):
        with self.assertRaisesRegex(ValueError, "regex needs"):
            generate.convert_rules({("regexp", "new-unsupported-pattern")}, set())


if __name__ == "__main__":
    unittest.main()
