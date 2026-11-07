# -*- coding: utf-8 -*-

"""ClassTool 的版本、构建与公开链接信息。"""

import json
import sys
from datetime import datetime
from pathlib import Path

from toolkit.core.app_logging import get_logger
from toolkit.core.paths import version_info_path
from toolkit.core.safe_io import read_text_with_fallback

FALLBACK_VERSION = "0.0.0"

GITHUB_URL = "https://github.com/Mario-Benny"
CHANGELOG_URL = "https://github.com/Mario-Benny/ClassTool/blob/main/CHANGELOG.md"


def _read_version() -> str:
    """读取 version.json 里的版本号。

    打不进包或文件写坏时回退成 0.0.0：关于页会直接把异常显示给使用者，比让主程序
    因为一个版本号文件起不来划算。
    """
    path = version_info_path()
    try:
        data = json.loads(read_text_with_fallback(path))
    except (OSError, ValueError) as exc:
        get_logger("app_info").error("版本信息读取失败 %s: %s", path, exc)
        return FALLBACK_VERSION

    version = data.get("version") if isinstance(data, dict) else None
    if not isinstance(version, str) or not version.strip():
        get_logger("app_info").error("版本信息缺少 version 字段: %s", path)
        return FALLBACK_VERSION

    return version.strip()


APP_VERSION = _read_version()


def build_date() -> str:
    """返回当前 EXE 或源码入口的最后修改日期。"""
    target = Path(sys.executable) if getattr(sys, "frozen", False) else Path(__file__)
    try:
        timestamp = target.stat().st_mtime
    except OSError:
        return "Unknown"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
