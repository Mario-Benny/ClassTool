# -*- coding: utf-8 -*-

"""应用日志：写入 data/logs，并接管未捕获异常。"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from toolkit.core.paths import ensure_log_dir

LOGGER_NAME = "classtool"
LOG_FILE_NAME = "classtool.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3

_file_ready = False
_setup_attempted = False


def setup_logging() -> bool:
    """创建文件日志。失败时保持无日志继续运行，绝不阻断启动。"""
    global _file_ready, _setup_attempted
    if _setup_attempted:
        return _file_ready

    _setup_attempted = True
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        handler = RotatingFileHandler(
            ensure_log_dir() / LOG_FILE_NAME,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        _file_ready = True
    except OSError:
        # 日志目录不可写不能反过来拖垮主程序，放弃文件日志继续启动。
        pass
    return _file_ready


def get_logger(name: str) -> logging.Logger:
    """返回挂在 classtool 命名空间下的记录器。"""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def install_excepthook() -> None:
    """让槽函数中的异常留下堆栈。

    PySide6 会把 Qt 槽里逃逸的异常交给 sys.excepthook，且不终止事件循环，
    因此没有这一步时首页空白之类的故障完全无法追溯。
    """
    logger = get_logger("crash")
    default_hook = sys.excepthook

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            default_hook(exc_type, exc, tb)
            return
        logger.critical("未捕获异常", exc_info=(exc_type, exc, tb))
        default_hook(exc_type, exc, tb)

    sys.excepthook = hook
