# -*- coding: utf-8 -*-

"""主程序设置的读取与保存。"""

import json
from pathlib import Path
from typing import Any

from toolkit.core.paths import settings_path


def _load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def _save_settings(data: dict[str, Any]) -> None:
    path = settings_path()
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temp_path.replace(path)


def get_all_settings() -> dict[str, Any]:
    """返回可安全导出的主程序设置副本。"""
    return dict(_load_settings())


def get_setting(key: str, default: Any = None) -> Any:
    """返回一个主程序设置；文件损坏时安全回退到默认值。"""
    return _load_settings().get(key, default)


def set_setting(key: str, value: Any) -> None:
    """原子写入一个主程序设置。"""
    data = _load_settings()
    data[key] = value
    _save_settings(data)


def replace_settings(data: dict[str, Any]) -> None:
    """使用已验证的字典整体替换主程序设置。"""
    if not isinstance(data, dict):
        raise ValueError("settings must be a dictionary")
    _save_settings(dict(data))


def reset_settings() -> None:
    """恢复主程序默认设置，不影响插件数据。"""
    _save_settings({})
