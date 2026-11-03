#!/usr/bin/env python3
"""Build the custom profile from Johnshall's current sr_backcn.conf."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
UPDATE_URL = "https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf"
SOURCE_REPOSITORY = "Johnshall/Shadowrocket-ADBlock-Rules-Forever"
SOURCE_BRANCH = "release"
SOURCE_FILE = "sr_backcn.conf"
LOCAL_NETWORKS = (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16", "224.0.0.0/4",
    "255.255.255.255/32", "::1/128", "fc00::/7", "fe80::/10", "ff00::/8",
)
RULE_TYPES = {
    "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD",
    "IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN", "RULE-SET", "DOMAIN-SET", "FINAL",
}


def download(url):
    request = Request(url, headers={"User-Agent": "shadowrocket-china-proxy"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def upstream_rules(source):
    section = None
    rules = []
    for raw in source.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            continue
        if section != "rule" or not line or line.startswith("#"):
            continue
        fields = [part.strip() for part in line.split(" #", 1)[0].split(",")]
        kind = fields[0].upper()
        if kind not in RULE_TYPES:
            raise ValueError(f"Unsupported upstream rule type needs review: {line}")
        policy_index = 1 if kind == "FINAL" else 2
        if len(fields) not in ({2} if kind == "FINAL" else {3, 4}):
            raise ValueError(f"Invalid upstream rule: {line}")
        fields[0] = kind
        fields[policy_index] = fields[policy_index].upper()
        if fields[policy_index] not in {"DIRECT", "PROXY"}:
            raise ValueError(f"Unexpected upstream routing policy: {line}")
        rules.append(",".join(fields))
    if not rules or rules[-1] != "FINAL,DIRECT" or sum(rule.startswith("FINAL,") for rule in rules) != 1:
        raise ValueError("Upstream return-China profile must end with one FINAL,DIRECT")
    for required in ("DOMAIN-SUFFIX,cn,PROXY", "GEOIP,CN,PROXY"):
        if required not in rules:
            raise ValueError(f"Upstream return-China profile is missing {required}")
    return rules


def render(source, revision, direct):
    rules = upstream_rules(source)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Shadowrocket China-return profile, adapted from Moshel and Johnshall.",
        f"# Upstream: https://github.com/{SOURCE_REPOSITORY}/blob/{revision}/{SOURCE_FILE}",
        f"# Generated: {generated}",
        f"# Upstream SHA256: {sha256(source.encode('utf-8')).hexdigest()}",
        "# Modified: persistent Doubao DIRECT overrides; local LAN bypass; system DNS; own update URL.",
        "# Google URL rewriting and MITM sections are omitted.",
        "# Adapted rules: CC BY-SA 4.0; see LICENSE.upstream.",
        "# PROXY follows the Home-screen server. Select a mainland China public-Internet exit.",
        "", "[General]", f"update-url = {UPDATE_URL}",
        "ipv6 = false", "dns-server = system",
        "skip-proxy = localhost, *.local, *.lan, *.internal",
        "tun-excluded-routes = " + ", ".join(LOCAL_NETWORKS),
        "", "[Rule]", "# 1. Persistent DIRECT overrides, before all upstream rules.",
    ]
    lines.extend(f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in sorted(direct))
    lines.extend(["", "# 2. Local network traffic stays DIRECT.", "DOMAIN,localhost,DIRECT"])
    lines.extend(f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in ("local", "lan", "internal"))
    lines.extend(f"IP-CIDR,{network},DIRECT,no-resolve" for network in LOCAL_NETWORKS)
    lines.extend(["", "# 3. Routing rules copied from the upstream sr_backcn.conf."])
    lines.extend(rules)
    return "\n".join(lines) + "\n"


def main():
    commit_url = f"https://api.github.com/repos/{SOURCE_REPOSITORY}/commits/{SOURCE_BRANCH}"
    revision = json.loads(download(commit_url))["sha"]
    base_url = f"https://raw.githubusercontent.com/{SOURCE_REPOSITORY}/{revision}"
    source = download(f"{base_url}/{SOURCE_FILE}").decode("utf-8")
    license_text = download(f"{base_url}/LICENSE").decode("utf-8")
    direct = {
        line.split("#", 1)[0].strip()
        for line in (ROOT / "direct-domains.txt").read_text().splitlines()
        if line.split("#", 1)[0].strip()
    }
    config = render(source, revision, direct)
    (ROOT / "sr_china_proxy.conf").write_text(config)
    (ROOT / "LICENSE.upstream").write_text(license_text.rstrip() + "\n")
    print(f"Generated from {SOURCE_REPOSITORY}@{revision}/{SOURCE_FILE}; {len(direct)} DIRECT overrides.")


if __name__ == "__main__":
    main()
