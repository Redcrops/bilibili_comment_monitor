# -*- coding: utf-8 -*-
"""从 get_dynamics_new 返回的 item 中提取 id、时间与文字。"""

from __future__ import annotations


def dynamic_item_id(item: dict) -> str:
    basic = item.get("basic") or {}
    return str(item.get("id_str") or basic.get("id_str") or "").strip()


def dynamic_pub_ts(item: dict) -> int:
    modules = item.get("modules") or {}
    author = modules.get("module_author") or {}
    try:
        return int(author.get("pub_ts") or 0)
    except (TypeError, ValueError):
        return 0


def dynamic_type_label(item: dict) -> str:
    basic = item.get("basic") or {}
    return str(basic.get("type") or item.get("type") or "未知")


def dynamic_url(item: dict) -> str:
    did = dynamic_item_id(item)
    if not did:
        return ""
    return f"https://www.bilibili.com/opus/{did}"


def dynamic_comment_oid(item: dict) -> int | None:
    """文字/图文动态的评论区 oid（basic.comment_id_str）。"""
    basic = item.get("basic") or {}
    raw = basic.get("comment_id_str") or basic.get("rid_str")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _nodes_to_text(nodes: list | None) -> str:
    if not nodes:
        return ""
    parts: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        text = node.get("text")
        if text:
            parts.append(str(text))
    return " ".join(parts).strip()


def _major_title(major: dict) -> str:
    for key in (
        "archive",
        "article",
        "pgc",
        "courses",
        "media_list",
        "live_rcmd",
        "common",
        "ugc_season",
    ):
        sub = major.get(key)
        if isinstance(sub, dict):
            title = (sub.get("title") or sub.get("name") or "").strip()
            if title:
                return title
    opus = major.get("opus")
    if isinstance(opus, dict):
        return str(opus.get("title") or "").strip()
    return ""


def _module_dynamic_text(module: dict | None) -> str:
    if not module:
        return ""
    parts: list[str] = []
    major = module.get("major")
    if isinstance(major, dict):
        title = _major_title(major)
        if title:
            parts.append(title)
        if major.get("type") == "MAJOR_TYPE_OPUS":
            opus = major.get("opus") or {}
            summary = opus.get("summary") or {}
            text = _nodes_to_text(summary.get("rich_text_nodes"))
            if text:
                parts.append(text)
    desc = module.get("desc") or {}
    text = _nodes_to_text(desc.get("rich_text_nodes"))
    if text:
        parts.append(text)
    return "\n".join(p for p in parts if p).strip()


def extract_dynamic_text(item: dict) -> str:
    modules = item.get("modules") or {}
    main = _module_dynamic_text(modules.get("module_dynamic"))
    orig = item.get("orig")
    if isinstance(orig, dict):
        orig_modules = orig.get("modules") or {}
        orig_text = _module_dynamic_text(orig_modules.get("module_dynamic"))
        if orig_text:
            if main:
                return f"{main}\n[转发] {orig_text}"
            return f"[转发] {orig_text}"
    return main or "(无文字)"
