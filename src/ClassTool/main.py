#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClassTool 主入口
"""

import sys
import ctypes
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from toolkit.ui.main_window import MainWindow
from toolkit.core.plugin_loader import PluginLoader
from toolkit.core.app_logging import get_logger, install_excepthook, setup_logging
from toolkit.core.instance_ipc import OpenToolServer, send_open_request, send_show_request
from toolkit.core.paths import ensure_runtime_dirs
from toolkit.core.tools_config import ensure_tools_config  # 确保配置文件存在

_INSTANCE_MUTEX_HANDLE = None
_logger = get_logger("main")


def ensure_single_instance() -> bool:
    """Windows 下只允许一个 ClassTool 实例运行。"""
    global _INSTANCE_MUTEX_HANDLE
    if sys.platform != "win32":
        return True

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p

    handle = kernel32.CreateMutexW(None, False, "Local\\ClassTool_Yexiaxingkong233_SingleInstance")
    if not handle:
        return True

    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False

    _INSTANCE_MUTEX_HANDLE = handle
    return True


def extract_tool_argument(argv: list[str]) -> tuple[list[str], str | None]:
    """取出 ``--tool <id>``，返回剩下的参数（含程序名）和插件标识。

    Qt 实测会静默忽略它认不出的长选项，但 ``-style`` 这类短选项是 Qt 自己的；把插件
    标识留在 argv 里等于依赖"Qt 恰好不认得 --tool"，所以在 QApplication 之前剥掉。
    """
    args = argv[1:]
    remaining: list[str] = list(argv[:1])
    tool_id: str | None = None
    index = 0

    while index < len(args):
        arg = args[index]
        if arg == "--tool":
            index += 1
            value = args[index] if index < len(args) else ""
        elif arg.startswith("--tool="):
            value = arg.split("=", 1)[1]
        else:
            remaining.append(arg)
            index += 1
            continue

        tool_id = value.strip() or None
        index += 1

    return remaining, tool_id


def main():
    # 日志与异常钩子必须最先建立，否则后续任何启动期故障都无从查证。
    setup_logging()
    install_excepthook()

    argv, tool_id = extract_tool_argument(sys.argv)

    if not ensure_single_instance():
        _forward_to_running_instance(tool_id)
        return

    # 确保运行目录和 data/tools_data.json 存在
    ensure_runtime_dirs()
    ensure_tools_config()

    app = QApplication(argv)
    app.setApplicationName("ClassTool")
    app.setOrganizationName("Yexiaxingkong233")

    def open_tool(requested_id: str) -> None:
        """唤起主窗口并切到指定插件页面。"""
        _logger.info("打开插件页面: %s", requested_id)
        window.show_and_raise()
        if requested_id not in window.loaded_plugins:
            # 右键菜单里的插件标识可能是上一次启动留下的，删掉插件后键还没刷新。
            _logger.warning("请求的插件不在当前列表中: %s", requested_id)
            return
        window.on_tool_clicked(requested_id)

    def show_main_window() -> None:
        """唤起已经运行的主窗口。"""
        _logger.info("收到显示主窗口请求")
        window.show_and_raise()

    # 监听排在插件扫描和建窗之前：第二个实例只能在等待预算内连上管道，
    # 冷启动越久越容易把请求丢掉。回调由事件循环投递，那时 window 已经建好。
    server = OpenToolServer(open_tool, show_main_window)
    server.start()

    loader = PluginLoader()
    window = MainWindow(loader)
    window.show()

    if tool_id:
        # 排在建窗之后：MainWindow 的首帧刷新会填 loaded_plugins，早一步就读不到插件。
        QTimer.singleShot(0, lambda: open_tool(tool_id))

    sys.exit(app.exec())


def _forward_to_running_instance(tool_id: str | None) -> None:
    """把本次启动的请求转交给已经运行的实例。"""
    if not tool_id:
        if send_show_request():
            _logger.info("已请求运行中的实例显示主窗口")
        else:
            _logger.warning("显示运行中实例的请求转交失败")
        return

    if send_open_request(tool_id):
        _logger.info("已把打开插件的请求转交给运行中的实例: %s", tool_id)
    else:
        _logger.warning("打开插件的请求转交失败: %s", tool_id)

if __name__ == "__main__":
    main()
