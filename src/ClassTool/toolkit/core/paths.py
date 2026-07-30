# -*- coding: utf-8 -*-

"""
程序路径工具。
"""

import sys
import tempfile
from pathlib import Path


def app_root() -> Path:
    """返回程序根目录，兼容源码运行和 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def ensure_tools_dir() -> Path:
    """返回 tools 目录，不存在时自动创建。"""
    tools_dir = app_root() / "tools"
    tools_dir.mkdir(exist_ok=True)
    return tools_dir


def ensure_data_dir() -> Path:
    """返回用户数据目录，位于程序根目录下。"""
    data_dir = app_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def tools_config_path() -> Path:
    """返回用户模块数据配置文件路径。"""
    return ensure_data_dir() / "tools_data.json"


def legacy_tools_config_path() -> Path:
    """返回旧版配置文件路径，仅用于迁移。"""
    return ensure_tools_dir() / "tools_data.json"


def ensure_tool_temp_dir() -> Path:
    """返回 Windows 临时目录下的 tool_temp 缓存目录。"""
    temp_dir = Path(tempfile.gettempdir()) / "tool_temp"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


def ensure_runtime_dirs():
    """确保运行时需要的轻量目录存在。"""
    ensure_tools_dir()
    ensure_data_dir()
    ensure_tool_temp_dir()
