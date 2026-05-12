# -*- coding: utf-8 -*-
"""统一标准输入输出为 UTF-8，避免 Windows 终端中文乱码。"""

from __future__ import annotations

import sys


def configure_stdio_utf8() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            # 65001 = UTF-8，改善 cmd.exe / 部分终端下的中文显示
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
