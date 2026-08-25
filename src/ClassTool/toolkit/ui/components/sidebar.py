# -*- coding: utf-8 -*-

"""固定的主导航侧栏。"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from .nav_button import NavButton


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(152)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 14, 10, 14)
        self.layout.setSpacing(4)

        self.nav_buttons = {}
        self.layout.addStretch()

    def add_nav_button(self, key: str, label: str):
        btn = NavButton(label)
        self.layout.insertWidget(self.layout.count() - 1, btn)
        self.nav_buttons[key] = btn
        return btn

    def apply_theme(self, theme: str, colors: dict[str, str]):
        for btn in self.nav_buttons.values():
            btn.apply_theme(theme, colors)
