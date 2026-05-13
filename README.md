# bilibili_comment_monitor

周期性监控 **最多 3 个 B 站 UP 主**各自 **当前最新公开稿件** 的评论区：当 **UP 本人**（`member.mid` 与目标 UID 一致）发表新评论时，可将摘要推送到 **飞书群机器人、B 站私信、短信 Webhook、Twilio** 等。

基于 Python 3 与 [bilibili-api-python](https://nemo2011.github.io/bilibili-api/)，评论拉取方式见官方文档中的 [`get_comments_lazy` 示例](https://nemo2011.github.io/bilibili-api/#/examples/comment)。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 多 UP | `target_mids` 数组，**最多 3 个**（也支持单字段 `target_mid` 或把 `target_mid` 写成数组） |
| 最新稿 | 每个 UP 按投稿时间取 **1 条最新视频** |
| 只看 UP 本人 | 含楼中楼里该 UP 的回复 |
| 去重 | 以评论 `rpid` 为准，换稿会重新首轮同步 |
| 首轮 / 增量 | 首轮在控制台打印 `[首轮]`（不写通知）；之后仅 **`[新评论]`** 触发通知，避免刷屏 |
| 时间 | 使用接口里的 `ctime` 格式化为本地可读时间，并入通知正文 |

更细的架构与状态设计见 [DESIGN.md](DESIGN.md)。

---

## 环境要求

- Python 3.10+（推荐）
- 网络能访问 B 站 API；如出现 **HTTP 412**，可尝试填写浏览器 Cookie、`enable_bili_ticket`、或更换网络/客户端指纹

---

## 安装

```bash
cd bilibili_comment_monitor
pip install -r requirements.txt
```

依赖含 `bilibili-api-python`、`curl_cffi`（推荐，用于请求栈与浏览器指纹）。

---

## 快速开始

1. 复制配置模板并编辑：

   ```bash
   copy config.example.json config.json
   ```

2. 在 `config.json` 中至少填写 **`target_mids`**（或 **`target_mid`**），例如：

   ```json
   "target_mids": [123456, 789012]
   ```

3. 运行：

   ```bash
   python monitor.py
   ```

默认读取**当前目录下** `config.json`，与配置文件**同目录**生成/更新 **`state.json`**（进度与去重，请勿把含 Cookie 的配置提交到 Git）。

---

## 命令行参数

| 参数 | 含义 |
|------|------|
| `-c` / `--config` | 配置文件路径，默认 `config.json` |
| `--once` | 只执行 **一轮** 检查后退出（联调） |
| `--rebootstrap` | 将各 UP 标为「未首轮同步」，**下一轮**重新走首轮并再次在终端打印 `[首轮]`（仍不通知）；用于想再看一遍历史输出而不手删 `state.json` |

示例：

```bash
python monitor.py -c config.json --once
python monitor.py --rebootstrap
```

---

## 配置说明（摘要）

完整字段以 **`config.example.json`** 为准。

| 区域 | 作用 |
|------|------|
| **target_mids** | 要监控的 UP 主 mid 列表，1～3 个 |
| **poll_interval_seconds** | 轮询间隔（秒） |
| **credential** | 浏览器 Cookie（`sessdata` 等）。拉多页评论、发私信时需要；其中 **发私信** 还需 **`bili_jct`** |
| **notify.bilibili_dm_receiver_uid** | 接收 B 站私信的对方 UID；`>0` 且凭据齐全时发送 |
| **notify.feishu_webhook_url** / **feishu_webhook_secret** | 飞书群自定义机器人 Webhook；开启签名校验时填写密钥 |
| **notify.sms_webhook_url** | 自建 POST 网关，`{"text","message"}` 与通知正文一致 |
| **notify.twilio** | 国际短信（需填全四项） |

---

## 日志与终端

- Windows 下已尽量将控制台切到 **UTF-8**，避免中文乱码；若仍异常可尝试先执行 `chcp 65001`。
- **历史评论**仅在每个 UP、每篇当前最新稿的 **首轮同步** 时，以 `[首轮]` 逐条打印一次；已同步后重启程序默认不再重复打印。需要再看一遍历史输出：使用 **`--rebootstrap`**，或删除 **`state.json`**。

---

## 免责声明

本项目仅供个人学习与小规模自用自动化；请遵守 [哔哩哔哩用户协议](https://www.bilibili.com/blackboard/topic/activity-cn8bxPLzz.html) 与相关法律法规，控制请求频率，勿用于骚扰或商业爬取。

---

## 相关文件

| 文件 | 说明 |
|------|------|
| [DESIGN.md](DESIGN.md) | 模块划分、状态结构、通知语义等设计说明 |
| `monitor.py` | 程序入口 |
| `config.example.json` | 配置模板 |
