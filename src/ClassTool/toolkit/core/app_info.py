# -*- coding: utf-8 -*-

"""ClassTool 的版本、构建与公开链接信息。"""

import sys
from datetime import datetime
from pathlib import Path


APP_VERSION = "1.1.0"
GITHUB_URL = "https://github.com/Mario-Benny"
CHANGELOG_URL = "https://github.com/Mario-Benny/ClassTool/blob/main/CHANGELOG.md"


def build_date() -> str:
    """返回当前 EXE 或源码入口的最后修改日期。"""
    target = Path(sys.executable) if getattr(sys, "frozen", False) else Path(__file__)
    try:
        timestamp = target.stat().st_mtime
    except OSError:
        return "Unknown"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
