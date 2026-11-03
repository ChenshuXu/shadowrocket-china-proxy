#!/usr/bin/env python3
"""Build an updateable Shadowrocket profile from v2fly's mainland China list."""

import argparse
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
UPDATE_URL = "https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf"
SOURCE_REPO = "https://github.com/v2fly/domain-list-community"
LOCAL_NETWORKS = (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16", "224.0.0.0/4",
    "255.255.255.255/32", "::1/128", "fc00::/7", "fe80::/10", "ff00::/8",
)


def download(url):
    request = Request(url, headers={"User-Agent": "shadowrocket-china-proxy"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def source_files(archive):
    with ZipFile(BytesIO(archive)) as package:
        prefix = package.namelist()[0].split("/")[0] + "/"
        files = {
            name[len(prefix + "data/"):]: package.read(name).decode("utf-8")
            for name in package.namelist()
            if name.startswith(prefix + "data/") and not name.endswith("/")
        }
        license_text = package.read(prefix + "LICENSE").decode("utf-8")
    return files, license_text


def expand_cn(files):
    # Affiliated rules can be included even if their target has no physical file.
    affiliations = {}
    for text in files.values():
        for line in text.splitlines():
            words = line.split("#", 1)[0].split()
            if not words or words[0].startswith("include:"):
                continue
            for flag in words[1:]:
                if flag.startswith("&"):
                    affiliations.setdefault(flag[1:], []).append(" ".join(words))

    @lru_cache(None)
    def expand(name):
        if name not in files and name not in affiliations:
            raise ValueError(f"Missing included domain list: {name}")
        lines = files.get(name, "").splitlines() + affiliations.get(name, [])
        result = []
        for line in lines:
            words = line.split("#", 1)[0].split()
            if not words:
                continue
            item, *flags = words
            attrs = frozenset(x[1:] for x in flags if x.startswith("@"))
            if item.startswith("include:"):
                for rule in expand(item[8:]):
                    if all(
                        (flag[2:] not in rule[2]) if flag.startswith("@-")
                        else (flag[1:] in rule[2])
                        for flag in flags if flag.startswith("@")
                    ):
                        result.append(rule)
            else:
                kind, value = item.split(":", 1) if ":" in item else ("domain", item)
                if kind not in {"domain", "full", "regexp"}:
                    raise ValueError(f"Unsupported upstream rule: {item}")
                result.append((kind, value.lower() if kind != "regexp" else value, attrs))
        return tuple(result)

    return {(kind, value) for kind, value, _ in expand("cn")}


def has_parent(name, suffixes):
    labels = name.split(".")
    return any(".".join(labels[index:]) in suffixes for index in range(1, len(labels)))


def convert_rules(rules, direct):
    suffixes = {value for kind, value in rules if kind == "domain"}
    exact = {value for kind, value in rules if kind == "full"}
    wildcards = set()
    for kind, value in rules:
        if kind != "regexp":
            continue
        if value == r"^.+-mihayo\.akamaized\.net$":
            wildcards.add("*-mihayo.akamaized.net")
        elif value == r".+\.awsdns-cn-[0-9][0-9]\.(biz|com|net|top)$":
            suffixes.update(f"awsdns-cn-{n:02d}.{tld}" for n in range(100) for tld in ("biz", "com", "net", "top"))
        elif value == r".+\.awsdns-cn-[0-9][a-e0-9]\.cn$" and "cn" in suffixes:
            pass  # Already covered by the cn suffix.
        else:
            raise ValueError(f"Upstream regex needs an explicit Shadowrocket conversion: {value}")
    suffixes = {value for value in suffixes if not has_parent(value, suffixes)}
    exact = {value for value in exact if value not in suffixes and not has_parent(value, suffixes)}
    suffixes = {value for value in suffixes if value not in direct and not has_parent(value, direct)}
    exact = {value for value in exact if value not in direct and not has_parent(value, direct)}
    return (
        [f"DOMAIN,{value},PROXY" for value in sorted(exact)]
        + [f"DOMAIN-SUFFIX,{value},PROXY" for value in sorted(suffixes)]
        + [f"DOMAIN-WILDCARD,{value},PROXY" for value in sorted(wildcards)]
    )


def render(archive, revision, direct):
    files, license_text = source_files(archive)
    rules = expand_cn(files)
    for domain in ("cn", "baidu.com", "bilibili.com", "qq.com", "taobao.com", "163.com", "jd.com"):
        if ("domain", domain) not in rules:
            raise ValueError(f"Upstream China list is missing expected domain: {domain}")
    china = convert_rules(rules, direct)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Shadowrocket China-return profile: Doubao DIRECT; other mainland China domains/IPs PROXY; other traffic DIRECT.",
        "# Reference: https://johnshall.github.io/Shadowrocket-ADBlock-Rules-Forever/sr_cnip.conf",
        f"# Generated: {generated}",
        f"# Domain source: {SOURCE_REPO}/tree/{revision}",
        f"# Source archive SHA256: {sha256(archive).hexdigest()}",
        "# Domain data: MIT License; see LICENSE.domain-list-community.",
        "# PROXY follows the Home-screen server. Select a mainland China public-Internet exit.",
        "", "[General]", f"update-url = {UPDATE_URL}",
        "ipv6 = false", "dns-server = system",
        "skip-proxy = localhost, *.local, *.lan, *.internal",
        "tun-excluded-routes = " + ", ".join(LOCAL_NETWORKS),
        "", "[Rule]", "# 1. Persistent DIRECT overrides (before China domains and GEOIP).",
    ]
    lines.extend(f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in sorted(direct))
    lines.extend(["", "# 2. Local network traffic stays DIRECT.", "DOMAIN,localhost,DIRECT"])
    lines.extend(f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in ("local", "lan", "internal"))
    lines.extend(f"IP-CIDR,{network},DIRECT,no-resolve" for network in LOCAL_NETWORKS)
    lines.extend(["", f"# 3. Mainland China domain snapshot: {len(china)} rules."] + china)
    lines.extend([
        "", "# 4. Resolve unknown domains for mainland China IP matching; do not add no-resolve.",
        "GEOIP,CN,PROXY", "", "# 5. Other destinations connect directly.", "FINAL,DIRECT", "",
    ])
    return "\n".join(lines), license_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an existing source ZIP for offline generation")
    parser.add_argument("--revision", default="master", help="Source revision for an offline archive")
    args = parser.parse_args()
    if args.archive:
        archive, revision = args.archive.read_bytes(), args.revision
    else:
        revision = json.loads(download("https://api.github.com/repos/v2fly/domain-list-community/commits/master"))["sha"]
        archive = download(f"https://codeload.github.com/v2fly/domain-list-community/zip/{revision}")
    direct = {
        line.split("#", 1)[0].strip()
        for line in (ROOT / "direct-domains.txt").read_text().splitlines()
        if line.split("#", 1)[0].strip()
    }
    config, license_text = render(archive, revision, direct)
    (ROOT / "sr_china_proxy.conf").write_text(config)
    (ROOT / "LICENSE.domain-list-community").write_text(license_text)
    print(f"Generated {len(config.splitlines())} lines from {revision}; {len(direct)} DIRECT overrides.")


if __name__ == "__main__":
    main()
