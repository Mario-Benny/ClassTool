# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Any

from toolkit.core.paths import legacy_tools_config_path, tools_config_path


def _get_config_path() -> Path:
    return tools_config_path()


def _migrate_legacy_config():
    path = _get_config_path()
    legacy_path = legacy_tools_config_path()
    if path.exists() or not legacy_path.exists():
        return

    try:
        path.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        _save_config({})


def _load_config() -> dict:
    _migrate_legacy_config()
    path = _get_config_path()
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def _save_config(data: dict):
    path = _get_config_path()
    tmp_path = path.with_name(path.name + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    tmp_path.replace(path)


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
