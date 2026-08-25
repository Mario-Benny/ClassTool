# -*- coding: utf-8 -*-

"""用于二选一设置项的分段选择控件。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    """固定宽度的二选一控件，适合主题和语言设置。"""

    value_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._buttons: dict[str, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def set_options(self, options: list[tuple[str, str]], value: str):
        """使用新的翻译文本刷新选项，并保持当前值。"""
        self._updating = True
        for button in self._buttons.values():
            self._button_group.removeButton(button)
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._buttons.clear()

        for index, (option_value, label) in enumerate(options):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setFixedHeight(34)
            button.setMinimumWidth(104)
            button.setObjectName("SegmentStart" if index == 0 else "SegmentEnd")
            button.setChecked(option_value == value)
            button.clicked.connect(
                lambda checked, selected=option_value: self._on_selected(checked, selected)
            )
            self._button_group.addButton(button)
            self._buttons[option_value] = button
            self._layout.addWidget(button)

        if not any(button.isChecked() for button in self._buttons.values()):
            first_button = next(iter(self._buttons.values()), None)
            if first_button is not None:
                first_button.setChecked(True)
        self._updating = False

    def _on_selected(self, checked: bool, value: str):
        if checked and not self._updating:
            self.value_changed.emit(value)

    def apply_theme(self, colors: dict[str, str]):
        """应用与当前程序主题一致的控件样式。"""
        selected_bg = "#0078d7" if colors["bg_main"] == "#1f1f1f" else "#0067b8"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {colors['bg_sidebar']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_main']};
                padding: 0 14px;
                font-size: 10pt;
            }}
            QPushButton#SegmentStart {{ border-top-left-radius: 4px; border-bottom-left-radius: 4px; }}
            QPushButton#SegmentEnd {{ border-top-right-radius: 4px; border-bottom-right-radius: 4px; margin-left: -1px; }}
            QPushButton:hover {{ background: {colors['bg_main']}; }}
            QPushButton:checked {{
                background: {selected_bg};
                color: white;
                border-color: {selected_bg};
            }}
        """)
