# -*- coding: utf-8 -*-

"""主程序多语言资源的加载、回退和切换。"""

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from toolkit.core.app_logging import get_logger
from toolkit.core.paths import language_dir
from toolkit.core.safe_io import read_text_with_fallback
from toolkit.core.settings import get_setting, set_setting


class LanguageManager(QObject):
    """从内置 JSON 语言包加载主程序文本。"""

    language_changed = Signal()

    DEFAULT_LANGUAGE = "zh_CN"

    def __init__(self) -> None:
        super().__init__()
        self._translations = self._load_languages()
        saved_language = get_setting("language", self.DEFAULT_LANGUAGE)
        self.current_language = (
            saved_language
            if saved_language in self._translations
            else self.DEFAULT_LANGUAGE
        )
        if self.current_language not in self._translations and self._translations:
            self.current_language = next(iter(self._translations))

    def _load_languages(self) -> dict[str, dict[str, str]]:
        languages: dict[str, dict[str, str]] = {}
        directory = language_dir()
        if not directory.is_dir():
            return languages

        for path in sorted(directory.glob("*.json")):
            translations = self._parse_language_file(path)
            if translations:
                languages[path.stem] = translations
        return languages

    @staticmethod
    def _parse_language_file(path: Path) -> dict[str, str]:
        """读一份语言包，出问题时丢掉这一份。

        不做损坏备份：这是随包资源，程序从不往回写，原件没有覆盖风险；丢掉之后
        translate 会自动回退到默认语言，再退化成翻译键本身，主程序照常能用。
        """
        try:
            data = json.loads(read_text_with_fallback(path))
        except (OSError, ValueError) as exc:
            get_logger("language").error("语言包读取失败 %s: %s", path, exc)
            return {}

        if not isinstance(data, dict):
            get_logger("language").error("语言包顶层不是对象: %s", path)
            return {}

        return {
            key: value
            for key, value in data.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def available_languages(self) -> list[tuple[str, str]]:
        """返回可用语言的内部标识和供用户阅读的名称。"""
        return [
            (code, texts.get("language.name", code))
            for code, texts in self._translations.items()
        ]

    def set_language(self, language_code: str) -> bool:
        """切换语言并持久化。返回值表示该语言是否可用。"""
        if language_code not in self._translations:
            return False
        if language_code == self.current_language:
            return True

        self.current_language = language_code
        set_setting("language", language_code)
        self.language_changed.emit()
        return True

    def translate(self, key: str, **values: object) -> str:
        """返回翻译文本，缺失时回退到中文，再回退到翻译键。"""
        current = self._translations.get(self.current_language, {})
        fallback = self._translations.get(self.DEFAULT_LANGUAGE, {})
        text = current.get(key, fallback.get(key, key))
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text
