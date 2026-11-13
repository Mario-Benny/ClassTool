# -*- coding: utf-8 -*-

"""在 ClassTool 完全退出后启动已经校验过的安装器。"""

import os
import subprocess
import sys
from pathlib import Path

from toolkit.core.app_logging import get_logger


_logger = get_logger("update_launcher")


def schedule_installer(installer_path: Path) -> bool:
    """启动一个脱离主进程的等待器，主程序退出后再请求管理员权限。"""
    if sys.platform != "win32":
        _logger.error("自动安装只支持 Windows")
        return False

    try:
        installer = installer_path.resolve(strict=True)
    except OSError as exc:
        _logger.error("更新安装器不存在: %s", exc)
        return False

    if not installer.is_file() or installer.suffix.lower() != ".exe":
        _logger.error("更新文件不是可执行安装器: %s", installer)
        return False

    escaped_path = str(installer).replace("'", "''")
    command = (
        f"Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue; "
        "Start-Sleep -Milliseconds 800; "
        f"Start-Process -FilePath '{escaped_path}' -Verb RunAs"
    )
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / (
        r"System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    if not powershell.is_file():
        _logger.error("找不到 Windows PowerShell: %s", powershell)
        return False

    creation_flags = 0x00000008 | 0x00000200 | 0x08000000
    try:
        subprocess.Popen(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                command,
            ],
            close_fds=True,
            creationflags=creation_flags,
        )
    except OSError as exc:
        _logger.error("无法创建更新启动器: %s", exc)
        return False

    _logger.info("已安排退出后启动更新安装器: %s", installer)
    return True

