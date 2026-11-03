# Shadowrocket 回国分流

每天同步 **[Johnshall/Shadowrocket-ADBlock-Rules-Forever 的回国规则 sr_backcn.conf](https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever/blob/release/sr_backcn.conf)**，并保留豆包和已确认语音接口优先直连的自定义例外。

## 配置链接

在 Shadowrocket「配置 → 右上角 +」中粘贴以下地址并下载：

```text
https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf
```

[查看配置](https://raw.githubusercontent.com/ChenshuXu/shadowrocket-china-proxy/main/sr_china_proxy.conf) · [更新运行记录](https://github.com/ChenshuXu/shadowrocket-china-proxy/actions/workflows/update.yml)

选中配置，将「全局路由」设为「配置 / Config」，首页选择中国大陆出口节点并连接。`PROXY` 跟随首页节点，节点须允许访问国内公网。配置不包含节点、订阅或凭据。

## 自动更新

1. GitHub Actions 每天读取上游 `release` 分支的最新提交，从同一提交下载 `sr_backcn.conf` 与许可文件，重新生成并验证后发布。也可手动运行；失败时继续提供上一份已发布的配置。
2. 在 Shadowrocket「设置」中开启**配置的自动后台更新**，间隔设为 **1 天**。GeoLite2 数据库的自动后台更新可同时开启，以刷新 IP 归属数据。
3. iPhone/iPad 需在系统「设置 → 通用 → 后台 App 刷新」中允许 Shadowrocket；实际后台更新时机受系统调度影响。也可点击配置的「更新配置」立即获取最新版。

配置内含 `update-url`；本地导入也保留更新地址。更新会覆盖本地改动，豆包例外保存在 [direct-domains.txt](direct-domains.txt)，每次生成都会保留。自动更新用法参考 [Shadowrocket 社区手册](https://github.com/LOWERTOP/Shadowrocket#自动更新)。

## 路由顺序

| 优先级 | 目标 | 策略 |
| --- | --- | --- |
| 1 | `doubao.com`、`doubaoapps.com`、`doubaocdn.com`、`doubao-dev.com` 及其子域名 | DIRECT |
| 1 | `openspeech.bytedance.com` 及其子域名 | DIRECT |
| 2 | 本地局域网、回环、链路本地地址 | DIRECT |
| 3 | 上游 `sr_backcn.conf` 的规则 | 按上游策略执行 |

当前上游的三条分流规则为：

```text
DOMAIN-SUFFIX,cn,PROXY
GEOIP,CN,PROXY
FINAL,DIRECT
```

因此，`.cn` 域名与中国大陆目标 IP 走代理，其他公网流量直连。**上游不含完整中国网站域名名单**：例如国内 `.com` 网站若解析到海外 CDN，按这份上游规则会直连。IP 归属由客户端 GeoIP 数据库判断，`GEOIP,CN,PROXY` 不加 `no-resolve`，以便解析域名后判断。

语音接口依据[火山引擎实时语音识别文档](https://docs.volcengine.com/docs/doubao-voice/bidirectional-streaming-automatic-speech-recognition-websocket?lang=zh)。尚未抓取豆包输入法的实际连接，语音速度和全部依赖覆盖尚未验证。

## 上游与本地改动

更新来源为 Johnshall 仓库的 **`release/sr_backcn.conf`**，这是该仓库为回国场景提供的无广告过滤版本。生成程序按原顺序读取 `[Rule]`，只统一策略名称的大小写，不再另外下载中国域名库。配置顶部记录上游提交和文件 SHA-256。

本地自定义包括：豆包/语音接口优先直连、私网直连、DNS 使用 `system`、保留 `ipv6 = false`、加入本配置的更新地址。上游的 Google URL 改写与 MITM 段不复制，无需安装解密证书。

规则由 Moshel、Johnshall 维护，本配置属于修改版本，依据上游 [CC BY-SA 4.0 许可](LICENSE.upstream) 发布；来源和修改内容也记录在配置顶部。

## 维护与验证

无需额外 Python 依赖：

```sh
python3 generate.py
python3 -m unittest -v test_generate.py
```

验证豆包直连优先级、中国 IP 与境外 IP 分流、上游新增规则同步、更新地址，以及误读为反向分流时停止发布。此验证不代表客户端真实连接或语音延迟验收。
