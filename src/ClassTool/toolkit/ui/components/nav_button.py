# -*- coding: utf-8 -*-

"""
导航按钮（侧边栏内），支持折叠时只显示图标
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QSizePolicy


class NavButton(QPushButton):
    def __init__(self, text: str, icon_char: str | None = None, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.icon_char = icon_char
        self.full_text = text
        self.is_collapsed = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.icon_label = QLabel(self.icon_char or "")
        self.icon_label.setFixedWidth(60)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("""
            font-family: 'Segoe MDL2 Assets';
            font-size: 12pt;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel(self.full_text)
        self.text_label.setStyleSheet("font-size: 11pt; background: transparent; border: none;")
        layout.addWidget(self.text_label)

        layout.addStretch()

        self.update_style()

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        self.text_label.setVisible(not collapsed)

    def update_style(self):
        # 增加圆角，更现代
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                outline: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 0.15);
                border-left: 4px solid #0078d7;
            }
        """)