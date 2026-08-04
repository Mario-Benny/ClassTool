#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ClassTool 主入口
"""

import sys
import ctypes
from PySide6.QtWidgets import QApplication
from toolkit.ui.main_window import MainWindow
from toolkit.core.plugin_loader import PluginLoader
from toolkit.core.paths import ensure_runtime_dirs
from toolkit.core.tools_config import ensure_tools_config  # 确保配置文件存在

_INSTANCE_MUTEX_HANDLE = None


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


def main():
    if not ensure_single_instance():
        return

    # 确保运行目录和 data/tools_data.json 存在
    ensure_runtime_dirs()
    ensure_tools_config()

    app = QApplication(sys.argv)
    app.setApplicationName("ClassTool")
    app.setOrganizationName("Yexiaxingkong233")

    loader = PluginLoader()
    window = MainWindow(loader)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
