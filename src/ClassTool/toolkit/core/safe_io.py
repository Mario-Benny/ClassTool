# -*- coding: utf-8 -*-

"""配置文件的原子写与损坏备份。"""

import secrets
from datetime import datetime
from pathlib import Path

from toolkit.core.app_logging import get_logger

# Windows 记事本的几种存盘方式：默认写带 BOM 的 UTF-8，"另存为 ANSI" 在中文系统上
# 写 GBK。硬编码 utf-8 会让教师仅仅改一个字就把文件读崩。
TEXT_ENCODINGS = ("utf-8-sig", "gbk")


def read_text_with_fallback(path: Path) -> str:
    """按记事本可能的编码依次尝试读取文本。

    全部失败时抛第一次（也就是最严格的 UTF-8）的 UnicodeDecodeError：调用方要给
    用户看的建议是"另存为 UTF-8"，配的原始错误也应当是 UTF-8 解不开那一条。
    """
    errors: list[UnicodeDecodeError] = []
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            errors.append(exc)

    raise errors[0]


def atomic_write_text(path: Path, text: str) -> None:
    """原子写入。

    临时名带随机后缀：固定名会让同一文件的所有写者（主程序与插件）落在同一个
    临时文件上，交叉写入时后完成的一方覆盖先完成的一方。
    """
    temp_path = path.with_name(f"{path.name}.{secrets.token_hex(4)}.tmp")
    try:
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
    except OSError:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            get_logger("safe_io").warning("临时文件清理失败: %s", temp_path)
        raise


def backup_corrupt(path: Path) -> Path | None:
    """把无法解析的文件改名保留下来。

    读取失败后调用方会回退成空字典，下一次写入随即覆盖原文件——不先移走原件，
    用户配置就在没有任何提示的情况下消失。用改名而不是复制，避免同一份坏文件
    被反复备份。
    """
    backup_path = path.with_name(
        f"{path.stem}.corrupt-{datetime.now():%Y%m%d-%H%M%S-%f}.bak"
    )
    try:
        path.replace(backup_path)
    except OSError as exc:
        get_logger("safe_io").error("损坏文件备份失败: %s (%s)", path, exc)
        return None

    get_logger("safe_io").error("配置文件无法解析，原件已保留为 %s", backup_path)
    return backup_path
