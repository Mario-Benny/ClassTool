# -*- coding: utf-8 -*-

"""侧边栏中的文本导航按钮。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QSizePolicy


class NavButton(QPushButton):
    def __init__(self, text: str, icon_char: str | None = None, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.full_text = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text_label = QLabel(self.full_text)
        self.text_label.setStyleSheet("font-size: 11pt; background: transparent; border: none; padding-left: 12px;")
        layout.addWidget(self.text_label)

        layout.addStretch()

    def set_text(self, text: str):
        """更新导航文字。"""
        self.full_text = text
        self.text_label.setText(text)

    def apply_theme(self, theme: str, colors: dict[str, str]):
        hover_bg = "rgba(255, 255, 255, 0.10)" if theme == "dark" else "#edf4fb"
        active_bg = "rgba(0, 120, 215, 0.24)" if theme == "dark" else "#dceeff"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                outline: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:checked {{
                background-color: {active_bg};
                border-left: 4px solid #0078d7;
            }}
        """)
        self.text_label.setStyleSheet(
            f"font-size: 11pt; color: {colors['text_primary']}; "
            "background: transparent; border: none; padding-left: 12px;"
        )
