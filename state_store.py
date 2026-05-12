# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MonitorState:
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
    def from_json(cls, data: dict) -> MonitorState:
        return cls(
            bvid=str(data.get("bvid", "") or ""),
            seen_rpids=set(int(x) for x in data.get("seen_rpids", []) if x is not None),
            bootstrapped=bool(data.get("bootstrapped", False)),
        )


def load_state(path: Path) -> MonitorState:
    if not path.is_file():
        return MonitorState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return MonitorState.from_json(data)


def save_state(path: Path, state: MonitorState) -> None:
    path.write_text(
        json.dumps(state.to_json(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
