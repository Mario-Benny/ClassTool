# -*- coding: utf-8 -*-

"""主程序设置的读取与保存。"""

import json
from copy import deepcopy
from typing import Any

from toolkit.core.app_logging import get_logger
from toolkit.core.paths import settings_path
from toolkit.core.safe_io import atomic_write_text, backup_corrupt, read_text_with_fallback


_settings_cache: dict[str, Any] | None = None


def _invalid_setting(key: str, strict: bool) -> None:
    message = f"设置项 {key!r} 的类型或值无效"
    if strict:
        raise ValueError(message)
    get_logger("settings").warning("%s，已忽略并使用默认值", message)


def _sanitize_settings(data: dict[str, Any], strict: bool = False) -> dict[str, Any]:
    """校验主程序认识的设置；未知字段原样保留以便向后兼容。"""
    result = deepcopy(data)

    theme = result.get("theme")
    if "theme" in result and (not isinstance(theme, str) or theme not in {"dark", "light"}):
        _invalid_setting("theme", strict)
        result.pop("theme", None)

    language = result.get("language")
    if "language" in result and (not isinstance(language, str) or not language.strip()):
        _invalid_setting("language", strict)
        result.pop("language", None)

    for key in ("close_to_tray", "context_menu_enabled", "auto_check_updates"):
        if key in result and not isinstance(result[key], bool):
            _invalid_setting(key, strict)
            result.pop(key, None)

    if "window_state" in result:
        state = result["window_state"]
        valid = isinstance(state, dict)
        if valid:
            for key in ("x", "y", "width", "height"):
                value = state.get(key)
                if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                    valid = False
                    break
            maximized = state.get("maximized")
            if maximized is not None and not isinstance(maximized, bool):
                valid = False
        if not valid:
            _invalid_setting("window_state", strict)
            result.pop("window_state", None)

    return result


def _load_settings() -> dict[str, Any]:
    global _settings_cache
    if _settings_cache is not None:
        return deepcopy(_settings_cache)

    path = settings_path()
    if not path.exists():
        _settings_cache = {}
        return {}

    try:
        text = read_text_with_fallback(path)
    except (OSError, UnicodeDecodeError) as exc:
        # 读不出内容时不备份：文件可能只是被占用或不是 UTF-8，移走它反而添乱。
        get_logger("settings").warning("设置文件读取失败: %s", exc)
        _settings_cache = {}
        return {}

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        backup_corrupt(path)
        get_logger("settings").error("设置文件不是合法 JSON: %s", exc)
        _settings_cache = {}
        return {}

    if not isinstance(data, dict):
        backup_corrupt(path)
        get_logger("settings").error("设置文件顶层不是对象，已按空设置继续运行")
        _settings_cache = {}
        return {}
    _settings_cache = _sanitize_settings(data)
    return deepcopy(_settings_cache)


def _save_settings(data: dict[str, Any]) -> None:
    global _settings_cache
    atomic_write_text(
        settings_path(),
        json.dumps(data, indent=2, ensure_ascii=False),
    )
    _settings_cache = deepcopy(data)


def get_all_settings() -> dict[str, Any]:
    """返回可安全导出的主程序设置副本。"""
    return deepcopy(_load_settings())


def get_setting(key: str, default: Any = None) -> Any:
    """返回一个主程序设置；文件损坏时安全回退到默认值。"""
    return deepcopy(_load_settings().get(key, default))


def set_setting(key: str, value: Any) -> None:
    """原子写入一个主程序设置。"""
    data = _load_settings()
    data[key] = value
    _save_settings(_sanitize_settings(data, strict=True))


def replace_settings(data: dict[str, Any]) -> None:
    """使用已验证的字典整体替换主程序设置。"""
    if not isinstance(data, dict):
        raise ValueError("settings must be a dictionary")
    _save_settings(_sanitize_settings(data, strict=True))


def reset_settings() -> None:
    """恢复主程序默认设置，不影响插件数据。"""
    _save_settings({})
