# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bilibili_api.utils.network import Credential

logger = logging.getLogger(__name__)


async def send_bilibili_dm(
    credential: Credential, receiver_uid: int, text: str
) -> None:
    if receiver_uid <= 0:
        return
    from bilibili_api import session as bsession
    from bilibili_api.session import EventType

    await bsession.send_msg(credential, receiver_uid, EventType.TEXT, text)
    logger.info("已发送 B 站私信 -> uid=%s", receiver_uid)


def _post_json(url: str, payload: dict, headers: dict[str, str]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 400:
            raise urllib.error.HTTPError(
                url, resp.status, resp.reason, resp.headers, None
            )


def send_sms_webhook(url: str, headers: dict[str, str], text: str) -> None:
    if not url:
        return
    _post_json(url, {"text": text, "message": text}, headers)
    logger.info("已请求短信 Webhook")


def send_feishu_webhook(url: str, secret: str, text: str) -> None:
    """飞书群自定义机器人：https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot"""
    if not url:
        return
    payload: dict[str, Any] = {
        "msg_type": "text",
        "content": {"text": text},
    }
    sec = (secret or "").strip()
    if sec:
        ts = str(int(time.time()))
        string_to_sign = f"{ts}\n{sec}"
        sign = base64.b64encode(
            hmac.new(
                sec.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode()
        payload["timestamp"] = ts
        payload["sign"] = sign

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        if resp.status >= 400:
            raise urllib.error.HTTPError(
                url, resp.status, resp.reason, resp.headers, None
            )
        try:
            out = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            logger.warning("飞书响应非 JSON，已忽略校码: %s", raw[:500])
            out = {}
        if "code" in out and int(out["code"]) != 0:
            raise RuntimeError(f"飞书 webhook 错误 code={out.get('code')}: {raw}")
        if "StatusCode" in out and int(out["StatusCode"]) != 0:
            raise RuntimeError(
                f"飞书 webhook StatusCode={out.get('StatusCode')}: {raw}"
            )
    logger.info("已发送到飞书机器人")


def send_twilio_sms(
    account_sid: str, auth_token: str, from_number: str, to: str, body: str
) -> None:
    if not (account_sid and auth_token and from_number and to):
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    form = urllib.parse.urlencode(
        {"From": from_number, "To": to, "Body": body}
    ).encode("utf-8")
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=form,
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 400:
            raise urllib.error.HTTPError(
                url, resp.status, resp.reason, resp.headers, None
            )
    logger.info("已通过 Twilio 发送短信 -> %s", to)
