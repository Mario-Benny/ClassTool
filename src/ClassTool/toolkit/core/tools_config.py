# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Any

from toolkit.core.app_logging import get_logger
from toolkit.core.paths import legacy_tools_config_path, tools_config_path
from toolkit.core.safe_io import atomic_write_text, backup_corrupt, read_text_with_fallback


def _get_config_path() -> Path:
    return tools_config_path()


def _migrate_legacy_config():
    path = _get_config_path()
    legacy_path = legacy_tools_config_path()
    if path.exists() or not legacy_path.exists():
        return

    try:
        atomic_write_text(path, read_text_with_fallback(legacy_path))
    except (OSError, UnicodeDecodeError):
        _save_config({})


def _load_config() -> dict:
    _migrate_legacy_config()
    path = _get_config_path()
    if not path.exists():
        return {}

    try:
        text = read_text_with_fallback(path)
    except (OSError, UnicodeDecodeError) as exc:
        get_logger("tools_config").warning("插件数据文件读取失败: %s", exc)
        return {}

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        backup_corrupt(path)
        get_logger("tools_config").error("插件数据文件不是合法 JSON: %s", exc)
        return {}

    if not isinstance(data, dict):
        backup_corrupt(path)
        get_logger("tools_config").error("插件数据文件顶层不是对象，已按空数据继续运行")
        return {}
    return data


def _save_config(data: dict):
    atomic_write_text(_get_config_path(), json.dumps(data, indent=2, ensure_ascii=False))


def ensure_tools_config():
    _migrate_legacy_config()
    if not _get_config_path().exists():
        _save_config({})


def get_tool_config(tool_name: str) -> Any:
    return _load_config().get(tool_name)


def set_tool_config(tool_name: str, value: Any):
    data = _load_config()
    data[tool_name] = value
    _save_config(data)


def delete_tool_config(tool_name: str):
    data = _load_config()
    if tool_name in data:
        del data[tool_name]
        _save_config(data)
