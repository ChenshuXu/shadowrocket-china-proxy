# Shadowrocket 回国分流

中国大陆域名和 IP 走回国代理，其他公网流量直连；**豆包及已确认的语音识别接口优先直连**。

## 配置链接

**在 Shadowrocket「配置 → 右上角 +」中粘贴以下地址并下载：**

```text
https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf
```

[查看配置](https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf) · [更新运行记录](https://github.com/ChenshuXu/shadowrocket-china-proxy/actions/workflows/update.yml)

选中配置，将「全局路由」设为「配置 / Config」，首页选择中国大陆出口节点并连接。`PROXY` 跟随首页节点；节点须允许访问国内公网。配置不包含节点、订阅或凭据。

## 自动更新

1. 本仓库通过 GitHub Actions **每天生成一次**最新版配置，也支持手动运行。生成或验证失败时不会发布新配置，现有链接继续提供上一份有效版本。
2. 在 Shadowrocket「设置」中开启**配置的自动后台更新**，间隔设为 **1 天**；GeoLite2 数据库的自动后台更新也可开启，以刷新 IP 归属数据。
3. iPhone/iPad 还需在系统「设置 → 通用 → 后台 App 刷新」中允许 Shadowrocket。后台更新时机受系统调度影响；也可点击配置的「更新配置」立即获取最新版。

配置内含 `update-url`，本地导入文件也会保留更新地址。更新时会覆盖本地改动；豆包直连例外保存在仓库的 [direct-domains.txt](direct-domains.txt)，每次生成都会保留。

自动更新用法参考 [Shadowrocket 社区手册](https://github.com/LOWERTOP/Shadowrocket#自动更新)。

## 路由顺序

| 优先级 | 目标 | 策略 |
| --- | --- | --- |
| 1 | `doubao.com`、`doubaoapps.com`、`doubaocdn.com`、`doubao-dev.com` 及其子域名 | DIRECT |
| 1 | `openspeech.bytedance.com` 及其子域名 | DIRECT |
| 2 | 本地局域网、回环、链路本地地址 | DIRECT |
| 3 | 中国大陆域名，包括国内网站使用的海外 CDN | PROXY |
| 4 | 未命中前面的域名规则，但目标 IP 属于中国大陆 | PROXY |
| 5 | 其他公网流量 | DIRECT |

语音接口依据[火山引擎实时语音识别文档](https://docs.volcengine.com/docs/doubao-voice/bidirectional-streaming-automatic-speech-recognition-websocket?lang=zh)。尚未抓取豆包输入法的实际连接，不能据此保证已经覆盖其所有依赖或验证语音速度。

沿用原配置的 `ipv6 = false`。本配置中私网地址直连，不包含家庭 VPN 专用路由。`GEOIP,CN,PROXY` 不加 `no-resolve`，以便解析不在域名名单中的网站并判断目标 IP。

## 为什么不直接提取原链接

[Johnshall 的 sr_cnip.conf](https://johnshall.github.io/Shadowrocket-ADBlock-Rules-Forever/sr_cnip.conf) 是本配置的分流方向参考。检查时其中国大陆判定只有 `GEOIP,CN,DIRECT`，没有中国大陆域名规则集可供提取。该 GeoIP 判定依赖客户端的数据库，原链接更新不等于它包含可提取的中国域名名单。

本仓库每天从 [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) 的最新提交展开 `cn`（`tld-cn` 与 `geolocation-cn`），遵循属性过滤（例如 `@-!cn`），去掉重复和被父域名覆盖的项，再应用优先直连例外。每份配置顶部记录生成时间、源提交和源下载包 SHA-256；域名数据的 [MIT 许可](LICENSE.domain-list-community) 随配置保留。

源名单中已知的三条正则规则被转换为 Shadowrocket 支持的通配符或显式域名；发现未知正则时停止生成，避免静默遗漏。外国网站强制代理条目、Google 域名改写和 MITM 段已移除，无需安装解密证书，也不增加广告过滤。

## 维护与验证

无需额外 Python 依赖：

```sh
python3 generate.py
python3 -m unittest -v test_generate.py
```

生成后先检查豆包直连、其他中外域名分类、例外优先级、更新地址、源名单过滤及 GeoIP/兜底顺序，通过后才提交发布。配置和自动生成流程的检查不代表客户端真实连接或语音延迟验收。
