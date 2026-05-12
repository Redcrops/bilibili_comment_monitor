# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

from bilibili_api import Credential, comment, get_client, get_selected_client, user, video
from bilibili_api.utils.network import request_settings
from bilibili_api.comment import CommentResourceType, OrderType
from bilibili_api.user import VideoOrder

from config import AppConfig, load_config
from encoding_utils import configure_stdio_utf8
from notify_channels import (
    send_bilibili_dm,
    send_feishu_webhook,
    send_sms_webhook,
    send_twilio_sms,
)
from state_store import MonitorState, load_state, save_state

logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"<[^>]+>")


def _plain_message(html: str) -> str:
    return _TAG_RE.sub("", html or "").replace("&nbsp;", " ").strip()


def _make_credential(cfg: AppConfig) -> Credential | None:
    c = cfg.credential
    if not c.is_nonempty():
        return None
    return Credential(
        sessdata=c.sessdata.strip(),
        bili_jct=(c.bili_jct.strip() or None),
        buvid3=(c.buvid3.strip() or None),
        buvid4=(c.buvid4.strip() or None),
        dedeuserid=(c.dedeuserid.strip() or None),
    )


def _setup_http_client(cfg: AppConfig) -> None:
    try:
        name, _ = get_selected_client()
    except Exception:
        logger.warning("未选择 HTTP 客户端，请安装 curl_cffi、httpx 或 aiohttp")
        return
    request_settings.set_enable_bili_ticket(cfg.enable_bili_ticket)
    logger.info("bilibili_api HTTP 客户端: %s, bili_ticket=%s", name, cfg.enable_bili_ticket)
    if name == "curl_cffi":
        get_client().set_impersonate(cfg.curl_impersonate)


def _flatten_replies(nodes: list | None):
    for r in nodes or []:
        yield r
        yield from _flatten_replies(r.get("replies"))


def _up_comments_from_replies(replies: list | None, up_mid: int) -> list[dict]:
    found = []
    for r in _flatten_replies(replies):
        if int(r.get("member", {}).get("mid", 0) or 0) == up_mid:
            found.append(r)
    return found


async def _iter_comment_chunks(
    aid: int,
    credential: Credential | None,
    max_pages: int,
):
    offset = ""
    cred = credential if credential is not None else Credential()
    for _ in range(max(1, max_pages)):
        chunk = await comment.get_comments_lazy(
            aid,
            CommentResourceType.VIDEO,
            offset=offset,
            order=OrderType.TIME,
            credential=cred,
        )
        Replies = chunk.get("replies")
        if Replies is None:
            logger.warning(
                "评论接口返回空（未登录时可能只能拉取前几页）；建议填写 credential"
            )
            break
        yield chunk
        cur = chunk.get("cursor") or {}
        if cur.get("is_end"):
            break
        pr = cur.get("pagination_reply") or {}
        nxt = pr.get("next_offset")
        if not nxt:
            break
        offset = nxt


async def _fetch_latest_video(cfg: AppConfig, cred: Credential | None) -> tuple[str, str]:
    u = user.User(cfg.target_mid, credential=cred if cred else Credential())
    res = await u.get_videos(pn=1, ps=1, order=VideoOrder.PUBDATE)
    vlist = res.get("list", {}).get("vlist") or []
    if not vlist:
        raise RuntimeError("未获取到该 UP 的投稿列表，请检查 target_mid 或网络环境")
    item = vlist[0]
    return str(item["bvid"]), str(item.get("title", ""))


async def _get_up_uname(cfg: AppConfig, cred: Credential | None) -> str:
    u = user.User(cfg.target_mid, credential=cred if cred else Credential())
    info = await u.get_user_info()
    return str(info.get("name", ""))


async def _bootstrap_state(
    cfg: AppConfig,
    state: MonitorState,
    bvid: str,
    up_uname: str,
    cred: Credential | None,
) -> None:
    v = video.Video(bvid=bvid, credential=cred if cred else Credential())
    aid = v.get_aid()
    n = 0
    async for chunk in _iter_comment_chunks(
        aid,
        cred,
        cfg.comment_scan.bootstrap_max_pages,
    ):
        ups = _up_comments_from_replies(chunk.get("replies"), cfg.target_mid)
        for r in ups:
            state.seen_rpids.add(int(r["rpid"]))
        n += 1
    state.bootstrapped = True
    logger.info(
        "已完成首轮同步（不会回溯通知）UP=%s 视频=%s 扫描约 %s 页 已记录 UP 评论 %s 条",
        up_uname,
        bvid,
        n,
        len(state.seen_rpids),
    )


async def _notify(cfg: AppConfig, cred: Credential | None, text: str) -> None:
    if cfg.notify.bilibili_dm_receiver_uid > 0:
        if not cred or not cred.bili_jct:
            logger.warning("已配置 bilibili_dm_receiver_uid 但缺少 bili_jct，跳过私信")
        else:
            try:
                await send_bilibili_dm(cred, cfg.notify.bilibili_dm_receiver_uid, text)
            except Exception:
                logger.exception("发送 B 站私信失败")

    if cfg.notify.sms_webhook_url:
        try:
            await asyncio.to_thread(
                send_sms_webhook,
                cfg.notify.sms_webhook_url,
                cfg.notify.sms_webhook_headers,
                text,
            )
        except Exception:
            logger.exception("短信 Webhook 请求失败")

    if cfg.notify.feishu_webhook_url:
        try:
            await asyncio.to_thread(
                send_feishu_webhook,
                cfg.notify.feishu_webhook_url,
                cfg.notify.feishu_webhook_secret,
                text,
            )
        except Exception:
            logger.exception("飞书 Webhook 请求失败")

    tw = cfg.notify.twilio
    if tw.account_sid and tw.auth_token and tw.from_number and tw.to:
        try:
            await asyncio.to_thread(
                send_twilio_sms,
                tw.account_sid,
                tw.auth_token,
                tw.from_number,
                tw.to,
                text,
            )
        except Exception:
            logger.exception("Twilio 短信发送失败")


async def run_cycle(
    cfg: AppConfig,
    state: MonitorState,
    state_path: Path,
    cred: Credential | None,
) -> None:
    bvid, title = await _fetch_latest_video(cfg, cred)
    up_uname = await _get_up_uname(cfg, cred)

    if state.bvid != bvid:
        logger.info("检测到最新稿件变化: %s -> %s (%s)", state.bvid, bvid, title)
        state.bvid = bvid
        state.seen_rpids.clear()
        state.bootstrapped = False
        save_state(state_path, state)

    if not state.bootstrapped:
        await _bootstrap_state(cfg, state, bvid, up_uname, cred)
        save_state(state_path, state)
        return

    v = video.Video(bvid=bvid, credential=cred if cred else Credential())
    aid = v.get_aid()
    new_rows: list[dict] = []

    async for chunk in _iter_comment_chunks(
        aid,
        cred,
        cfg.comment_scan.max_pages_per_poll,
    ):
        for r in _up_comments_from_replies(chunk.get("replies"), cfg.target_mid):
            rid = int(r["rpid"])
            if rid not in state.seen_rpids:
                new_rows.append(r)
                state.seen_rpids.add(rid)

    new_rows.sort(key=lambda x: int(x.get("ctime", 0)))

    for r in new_rows:
        body = _plain_message((r.get("content") or {}).get("message", ""))
        url = f"https://www.bilibili.com/video/{bvid}"
        text = (
            f"【UP主新评论】{up_uname}\n"
            f"视频: {title}\n"
            f"内容: {body}\n"
            f"{url}"
        )
        logger.info("新评论 rpid=%s 内容:\n%s", r["rpid"], body or "(空)")
        await _notify(cfg, cred, text)

    if new_rows:
        save_state(state_path, state)


async def amain(config_path: Path, once: bool) -> None:
    cfg = load_config(config_path)
    _setup_http_client(cfg)
    cred = _make_credential(cfg)
    state_path = config_path.resolve().parent / "state.json"
    state = load_state(state_path)

    logger.info(
        "开始监控 UP mid=%s，轮询间隔 %ss",
        cfg.target_mid,
        cfg.poll_interval_seconds,
    )
    while True:
        try:
            await run_cycle(cfg, state, state_path, cred)
        except Exception:
            logger.exception("本轮检查失败")
        if once:
            break
        await asyncio.sleep(cfg.poll_interval_seconds)


def main() -> None:
    configure_stdio_utf8()
    parser = argparse.ArgumentParser(
        description="监控指定 UP 最新视频下该 UP 主发表的评论，并发送 B 站私信与短信"
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="配置文件路径（默认 ./config.json）",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只执行一轮检查（用于联调）",
    )
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_file():
        print(
            f"未找到配置文件: {config_path.resolve()}\n"
            f"请复制 config.example.json 为 config.json 并修改 target_mid 等字段。",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    try:
        asyncio.run(amain(config_path, args.once))
    except KeyboardInterrupt:
        logger.info("已退出")


if __name__ == "__main__":
    main()
