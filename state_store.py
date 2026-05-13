# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UpMonitorState:
    bvid: str = ""
    seen_rpids: set[int] = field(default_factory=set)
    bootstrapped: bool = False

    def to_json(self) -> dict:
        return {
            "bvid": self.bvid,
            "seen_rpids": sorted(self.seen_rpids),
            "bootstrapped": self.bootstrapped,
        }

    @classmethod
    def from_json(cls, data: dict) -> UpMonitorState:
        return cls(
            bvid=str(data.get("bvid", "") or ""),
            seen_rpids=set(
                int(x) for x in data.get("seen_rpids", []) if x is not None
            ),
            bootstrapped=bool(data.get("bootstrapped", False)),
        )


@dataclass
class RootState:
    """按 UP mid 分片；键为十进制 mid 字符串。"""

    ups: dict[str, UpMonitorState] = field(default_factory=dict)

    def slice_for(self, mid: int) -> UpMonitorState:
        return self.ups.setdefault(str(mid), UpMonitorState())

    def to_json(self) -> dict:
        return {"ups": {k: v.to_json() for k, v in sorted(self.ups.items())}}

    @classmethod
    def from_json(cls, data: dict) -> RootState:
        ups_raw = data.get("ups")
        if not isinstance(ups_raw, dict):
            return cls()
        return cls(
            ups={str(k): UpMonitorState.from_json(v) for k, v in ups_raw.items()}
        )


def load_state(path: Path, target_mids: list[int]) -> RootState:
    log = logging.getLogger(__name__)
    if not path.is_file():
        return RootState()
    data = json.loads(path.read_text(encoding="utf-8"))
    if "ups" in data and isinstance(data["ups"], dict):
        return RootState.from_json(data)
    # 旧版单 UP：整份 JSON 即一个 UpMonitorState
    if len(target_mids) == 1:
        only = str(target_mids[0])
        return RootState(ups={only: UpMonitorState.from_json(data)})
    log.warning(
        "state.json 为旧格式且当前配置了多个 UP，已忽略旧状态，将重新首轮同步"
    )
    return RootState()


def save_state(path: Path, state: RootState) -> None:
    path.write_text(
        json.dumps(state.to_json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
