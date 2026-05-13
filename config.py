# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_MAX_UPS = 3


@dataclass
class CommentScanConfig:
    max_pages_per_poll: int = 3
    bootstrap_max_pages: int = 15


@dataclass
class CredentialConfig:
    sessdata: str = ""
    bili_jct: str = ""
    dedeuserid: str = ""
    buvid3: str = ""
    buvid4: str = ""

    def is_nonempty(self) -> bool:
        return bool(self.sessdata and self.sessdata.strip())


@dataclass
class TwilioConfig:
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""
    to: str = ""


@dataclass
class NotifyConfig:
    bilibili_dm_receiver_uid: int = 0
    sms_webhook_url: str = ""
    sms_webhook_headers: dict[str, str] = field(default_factory=dict)
    feishu_webhook_url: str = ""
    feishu_webhook_secret: str = ""
    twilio: TwilioConfig = field(default_factory=TwilioConfig)


@dataclass
class AppConfig:
    target_mids: list[int]
    poll_interval_seconds: int = 90
    curl_impersonate: str = "chrome136"
    enable_bili_ticket: bool = False
    comment_scan: CommentScanConfig = field(default_factory=CommentScanConfig)
    credential: CredentialConfig = field(default_factory=CredentialConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)


def _normalize_target_mids(raw: dict[str, Any]) -> list[int]:
    if "target_mids" in raw and isinstance(raw["target_mids"], list):
        xs = [int(x) for x in raw["target_mids"]]
    elif "target_mid" in raw:
        xs = [int(raw["target_mid"])]
    else:
        raise ValueError("配置需包含 target_mid（单个）或 target_mids（数组，最多3个）")
    seen: set[int] = set()
    out: list[int] = []
    for m in xs:
        if m not in seen:
            seen.add(m)
            out.append(m)
    if not out:
        raise ValueError("target_mids 不能为空")
    if len(out) > _MAX_UPS:
        raise ValueError(f"最多支持 {_MAX_UPS} 个 UP 主，当前 {len(out)} 个")
    return out


def _dig(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    target_mids = _normalize_target_mids(raw)
    tw = _dig(raw, "notify", "twilio", default={}) or {}
    return AppConfig(
        target_mids=target_mids,
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 90)),
        curl_impersonate=str(raw.get("curl_impersonate", "chrome136")),
        enable_bili_ticket=bool(raw.get("enable_bili_ticket", False)),
        comment_scan=CommentScanConfig(
            max_pages_per_poll=int(
                _dig(raw, "comment_scan", "max_pages_per_poll", default=3)
            ),
            bootstrap_max_pages=int(
                _dig(raw, "comment_scan", "bootstrap_max_pages", default=15)
            ),
        ),
        credential=CredentialConfig(
            sessdata=str(_dig(raw, "credential", "sessdata", default="") or ""),
            bili_jct=str(_dig(raw, "credential", "bili_jct", default="") or ""),
            dedeuserid=str(_dig(raw, "credential", "dedeuserid", default="") or ""),
            buvid3=str(_dig(raw, "credential", "buvid3", default="") or ""),
            buvid4=str(_dig(raw, "credential", "buvid4", default="") or ""),
        ),
        notify=NotifyConfig(
            bilibili_dm_receiver_uid=int(
                _dig(raw, "notify", "bilibili_dm_receiver_uid", default=0)
            ),
            sms_webhook_url=str(
                _dig(raw, "notify", "sms_webhook_url", default="") or ""
            ).strip(),
            sms_webhook_headers=dict(
                _dig(raw, "notify", "sms_webhook_headers", default={}) or {}
            ),
            feishu_webhook_url=str(
                _dig(raw, "notify", "feishu_webhook_url", default="") or ""
            ).strip(),
            feishu_webhook_secret=str(
                _dig(raw, "notify", "feishu_webhook_secret", default="") or ""
            ).strip(),
            twilio=TwilioConfig(
                account_sid=str(tw.get("account_sid", "") or ""),
                auth_token=str(tw.get("auth_token", "") or ""),
                from_number=str(tw.get("from", "") or ""),
                to=str(tw.get("to", "") or ""),
            ),
        ),
    )
