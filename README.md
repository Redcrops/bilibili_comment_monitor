# bilibili_comment_monitor

周期性监控 **最多 3 个 B 站 UP 主**的 **最新稿件评论区**（UP 本人发言）与 **空间动态**（文字内容）。新评论可推送到飞书/私信/短信等；**新动态** 输出到终端并推飞书。

基于 Python 3 与 [bilibili-api-python](https://nemo2011.github.io/bilibili-api/)，评论拉取方式见官方文档中的 [`get_comments_lazy` 示例](https://nemo2011.github.io/bilibili-api/#/examples/comment)。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 多 UP | `target_mids` 数组，**最多 3 个**（也支持单字段 `target_mid` 或把 `target_mid` 写成数组） |
| 最新稿 | 每个 UP 按投稿时间取 **1 条最新视频**，监控其评论区 UP 本人发言 |
| 空间动态 | 每个 UP 的空间动态（`get_dynamics_new`），提取文字内容 |
| 只看 UP 本人 | 含楼中楼里该 UP 的回复 |
| 去重 | 以评论 `rpid` 为准，换稿会重新首轮同步 |
| 首轮 / 增量 | 评论：`[首轮]` / `[新评论]`；动态首轮**仅终端展示最新 1 条**（不推飞书），之后 **`[新动态]`** 才推飞书 |
| 通知 | **仅新发**评论/动态推飞书；评论还可走私信/短信等；首轮同步一律不推飞书 |
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
| `--rebootstrap` | 重新首轮同步评论与动态，再次打印 `[首轮]` / `[首轮动态]`（仍不通知） |

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
| **comment_scan** / **dynamic_scan** | 评论分页与动态轮询条数（`max_*`）；动态首轮固定只展示最新 1 条 |
| **credential** | 浏览器 Cookie（`sessdata` 等）。拉多页评论、发私信时需要；其中 **发私信** 还需 **`bili_jct`** |
| **notify.bilibili_dm_receiver_uid** | 接收 B 站私信的对方 UID；`>0` 且凭据齐全时发送 |
| **notify.feishu_webhook_url** / **feishu_webhook_secret** | 飞书群自定义机器人 Webhook；开启签名校验时填写密钥 |
| **notify.sms_webhook_url** | 自建 POST 网关，`{"text","message"}` 与通知正文一致 |
| **notify.twilio** | 国际短信（需填全四项） |

---

## 日志与终端

- Windows 下已尽量将控制台切到 **UTF-8**，避免中文乱码；若仍异常可尝试先执行 `chcp 65001`。
- **历史评论/动态**仅在首轮同步时打印；已同步后重启默认不再重复。需要再看：`python monitor.py --rebootstrap` 或删除 `state.json`。

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
