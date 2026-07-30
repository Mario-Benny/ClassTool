# -*- coding: utf-8 -*-

"""
侧边栏组件，包含导航按钮和折叠功能
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from .nav_button import NavButton


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(200)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.hamburger_btn = QPushButton("\uE700")
        self.hamburger_btn.setFixedSize(60, 48)
        self.hamburger_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-family: 'Segoe MDL2 Assets';
                font-size: 12pt;
                text-align: center;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
        """)
        self.layout.addWidget(self.hamburger_btn)

        self.nav_buttons = {}
        self.layout.addStretch()

    def add_nav_button(self, key: str, label: str, icon: str):
        btn = NavButton(label, icon)
        self.layout.insertWidget(self.layout.count() - 1, btn)
        self.nav_buttons[key] = btn
        return btn

    def set_collapsed(self, collapsed: bool):
        for btn in self.nav_buttons.values():
            btn.set_collapsed(collapsed)