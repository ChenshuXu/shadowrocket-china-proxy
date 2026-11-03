# Shadowrocket 中国大陆 IP 分流

每天读取 **[Johnshall/Shadowrocket-ADBlock-Rules-Forever 的 sr_cnip.conf](https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever/blob/release/sr_cnip.conf)**，转换为：中国大陆 IP 走代理，其他 IP 直连；保留豆包和已确认语音接口优先直连的例外。

## 配置链接

在 Shadowrocket「配置 → 右上角 +」中粘贴以下地址并下载：

```text
https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf
```

[查看配置](https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf) · [自动更新记录](https://github.com/ChenshuXu/shadowrocket-china-proxy/actions/workflows/update.yml)

选中配置，将「全局路由」设为「配置 / Config」，首页选择中国大陆出口节点并连接。`PROXY` 跟随首页节点，节点须允许访问国内公网。配置不包含节点、订阅或凭据。

## 从 sr_cnip.conf 转换的方式

| 原始规则 | 转换后 |
| --- | --- |
| `GEOIP,CN,DIRECT` | `GEOIP,CN,PROXY` |
| 外国域名、IP 的显式 `PROXY` 规则 | 改为 `DIRECT`，放在中国 IP 判断之后 |
| `FINAL,PROXY` | `FINAL,DIRECT` |

中国 IP 判断放在原有外国域名规则之前，因此外国域名若解析到中国大陆 IP，也会走代理。没有额外添加 `.cn` 域名代理规则：**`.cn` 网站若解析到境外 IP，也会直连**。IP 归属由 Shadowrocket 的 GeoIP 数据库判断，`GEOIP,CN,PROXY` 不加 `no-resolve`，以便对域名解析后判断。

更新来源固定为 `release/sr_cnip.conf`，不读取 `sr_backcn.conf` 或其他中国域名库。配置顶部记录上游提交及源文件 SHA-256。

## 最终路由顺序

| 优先级 | 目标 | 策略 |
| --- | --- | --- |
| 1 | `doubao.com`、`doubaoapps.com`、`doubaocdn.com`、`doubao-dev.com` 及其子域名 | DIRECT |
| 1 | `openspeech.bytedance.com` 及其子域名 | DIRECT |
| 2 | 局域网、回环、链路本地地址 | DIRECT |
| 3 | 中国大陆目标 IP | PROXY |
| 4 | 原配置中的其他显式域名/IP 规则 | DIRECT |
| 5 | 其余流量 | DIRECT |

豆包直连例外保存在 [direct-domains.txt](direct-domains.txt)，每次更新都会保留。语音接口依据[火山引擎文档](https://docs.volcengine.com/docs/doubao-voice/bidirectional-streaming-automatic-speech-recognition-websocket?lang=zh)；豆包输入法实际连接及语音延迟尚未验收。

保留本配置的系统 DNS、`ipv6 = false`、私网直连和更新地址。原配置的 Google URL 改写与 MITM 段不复制，不需要解密证书。

## 自动更新

1. GitHub Actions 每天从上游 `release` 分支同一最新提交下载 `sr_cnip.conf` 与许可文件，转换、验证后发布。也支持手动运行，失败时保留上一份已发布版本。
2. 在 Shadowrocket「设置」中开启**配置的自动后台更新**，间隔设为 **1 天**。可同时开启 GeoLite2 数据库自动后台更新，以刷新 IP 归属数据。
3. iPhone/iPad 需在系统「设置 → 通用 → 后台 App 刷新」中允许 Shadowrocket。后台更新时间受系统调度影响；也可点击配置的「更新配置」立即获取最新版。

配置中含 `update-url`，本地文件导入也保留更新地址。自动更新会覆盖本地改动。相关设置见 [Shadowrocket 社区手册](https://github.com/LOWERTOP/Shadowrocket#自动更新)。

## 维护与验证

无需额外 Python 依赖：

```sh
python3 generate.py
python3 -m unittest -v test_generate.py
```

检查源文件固定为 `sr_cnip.conf`、只有中国 GeoIP 规则使用 `PROXY`、原外国域名解析到中国 IP 时代理、`.cn` 域名解析到境外 IP 时直连、豆包例外优先，以及上游新增条目的转换。源文件格式或分流方向不符时停止发布。

原规则由 Moshel、Johnshall 维护，本配置为修改版本，依据上游 [CC BY-SA 4.0 许可](LICENSE.upstream) 发布。配置检查不代表客户端真实连接或语音延迟验收。
