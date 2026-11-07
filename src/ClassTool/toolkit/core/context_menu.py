# -*- coding: utf-8 -*-

"""桌面空白处右键菜单的注册与移除。

只写当前用户的 HKCU，不需要管理员权限，也不影响其他账户：

    HKCU\\Software\\Classes\\DesktopBackground\\shell\\ClassTool
        MUIVerb      = "ClassTool"
        SubCommands  = ""                 # 空字符串才会被 Explorer 渲染成级联子菜单
        shell\\01_<tool_id>
            MUIVerb  = "<工具名称>"
            command\\(默认) = "<启动命令> --tool <tool_id>"

键名前面的两位数字只用于排序：Explorer 按子键名的字典序排列，与显示文字和首页
顺序都无关。真实插件标识只出现在 command 里，不参与排序。
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Any, Iterable

from toolkit.core.app_logging import get_logger
from toolkit.core.paths import app_root

try:
    import winreg
except ImportError:  # 非 Windows 平台：仅保证模块可以被静态导入
    winreg = None

_logger = get_logger("context_menu")

REGISTRY_ROOT = r"Software\Classes\DesktopBackground\shell\ClassTool"
SUBCOMMANDS_FOLDER = "shell"
MENU_TEXT = "ClassTool"

# 默认关闭：主程序不在首次启动时悄悄写注册表。可以在设置页打开，或运行随包的
# “启用桌面右键菜单.cmd”；安装器将来也可以把它做成一个可选组件。
DEFAULT_ENABLED = False

SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000
SHCNF_FLUSH = 0x1000


def _escape_mnemonic(text: str) -> str:
    """菜单文字里的 & 是助记符，写入前必须转义成 && 才会原样显示。"""
    return text.replace("&", "&&")


def _command_line(tool_id: str) -> str:
    """返回写进注册表的启动命令。

    打包后直接调用 EXE；源码运行时优先用 pythonw.exe，避免每次右键点击都闪一下
    控制台窗口。插件标识加引号，防止第三方插件文件名里带空格。
    """
    if getattr(sys, "frozen", False):
        program = Path(sys.executable)
        return f'"{program}" --tool "{tool_id}"'

    script = app_root() / "main.py"
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else python
    return f'"{launcher}" "{script}" --tool "{tool_id}"'


def _valid_tools(tools: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """过滤掉加载失败的错误磁贴：放进菜单只会点出一声报错。"""
    result: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        tool_id = tool.get("id")
        if not isinstance(tool_id, str) or not tool_id.strip():
            continue
        if tool.get("error"):
            continue
        result.append(tool)
    return result


def _build_entries(tools: Iterable[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """生成 ``(键名, 菜单文字, 启动命令)`` 列表，顺序即首页加载顺序。"""
    entries: list[tuple[str, str, str]] = []
    for index, tool in enumerate(_valid_tools(tools), start=1):
        tool_id = tool["id"].strip()
        name = tool.get("name")
        if not isinstance(name, str) or not name.strip():
            name = tool_id
        entries.append(
            (f"{index:02d}_{tool_id}", name.strip(), _command_line(tool_id))
        )
    return entries


def _delete_tree(path: str) -> None:
    """递归删除一个注册表键；键不存在时静默返回。"""
    if winreg is None:
        return

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WRITE
        ) as key:
            names: list[str] = []
            index = 0
            while True:
                try:
                    names.append(winreg.EnumKey(key, index))
                except OSError:
                    break
                index += 1
    except FileNotFoundError:
        return
    except OSError as exc:
        _logger.warning("无法打开右键菜单注册键 %s: %s", path, exc)
        return

    # 先收集名字再删除：边枚举边删会让后续子键的索引前移，漏掉一部分。
    for name in names:
        _delete_tree(f"{path}\\{name}")

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        _logger.warning("删除右键菜单注册键失败 %s: %s", path, exc)


def notify_shell() -> None:
    """通知资源管理器刷新关联信息，让菜单增删尽快可见。"""
    if sys.platform != "win32":
        return
    try:
        shell32 = ctypes.windll.shell32
        shell32.SHChangeNotify.argtypes = [
            ctypes.c_long,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        shell32.SHChangeNotify.restype = None
        shell32.SHChangeNotify(
            SHCNE_ASSOCCHANGED, SHCNF_IDLIST | SHCNF_FLUSH, None, None
        )
    except Exception as exc:
        # 刷新失败只影响菜单出现的时间，不影响注册表内容本身。
        _logger.warning("通知资源管理器刷新右键菜单失败: %s", exc)


def register(tools: Iterable[dict[str, Any]]) -> bool:
    """按当前插件列表整棵重建桌面右键菜单，成功返回 True。

    先删后建：插件增删、改名或安装目录搬家都不会留下指向旧路径的脏键。
    没有可用插件时不写一个空的顶层菜单，直接移除。
    """
    if winreg is None:
        _logger.warning("当前平台不支持注册表操作，跳过右键菜单注册")
        return False

    entries = _build_entries(tools)
    if not entries:
        _logger.info("没有可用插件，移除桌面右键菜单")
        unregister()
        return False

    try:
        _delete_tree(REGISTRY_ROOT)

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, REGISTRY_ROOT, 0, winreg.KEY_WRITE
        ) as menu_key:
            winreg.SetValueEx(menu_key, "MUIVerb", 0, winreg.REG_SZ, MENU_TEXT)
            # 空字符串是级联菜单的开关；删掉这个值 Explorer 会把它当普通菜单项。
            winreg.SetValueEx(menu_key, "SubCommands", 0, winreg.REG_SZ, "")

        container_path = f"{REGISTRY_ROOT}\\{SUBCOMMANDS_FOLDER}"
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, container_path, 0, winreg.KEY_WRITE
        ):
            pass

        for key_name, label, command in entries:
            item_path = f"{container_path}\\{key_name}"
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, item_path, 0, winreg.KEY_WRITE
            ) as item_key:
                winreg.SetValueEx(
                    item_key, "MUIVerb", 0, winreg.REG_SZ, _escape_mnemonic(label)
                )
                with winreg.CreateKeyEx(
                    winreg.HKEY_CURRENT_USER,
                    f"{item_path}\\command",
                    0,
                    winreg.KEY_WRITE,
                ) as command_key:
                    winreg.SetValueEx(command_key, None, 0, winreg.REG_SZ, command)
    except OSError as exc:
        _logger.warning("桌面右键菜单注册失败: %s", exc)
        return False

    _logger.info("桌面右键菜单已注册: %d 项", len(entries))
    notify_shell()
    return True


def unregister() -> bool:
    """删除整棵菜单子树；键本来就不存在时同样返回 True。"""
    if winreg is None:
        _logger.warning("当前平台不支持注册表操作，跳过右键菜单移除")
        return False

    _delete_tree(REGISTRY_ROOT)
    _logger.info("桌面右键菜单已移除")
    notify_shell()
    return True
