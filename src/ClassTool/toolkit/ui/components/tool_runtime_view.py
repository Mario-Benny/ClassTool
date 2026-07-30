# -*- coding: utf-8 -*-

"""
工具运行时视图：显示工具标题和工具返回的 widget
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from toolkit.ui.utils import clear_layout


class ToolRuntimeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        header = QHBoxLayout()
        self.back_btn = QPushButton("\uE72B 返回工具列表")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                color: white;
                font-family: 'Segoe MDL2 Assets', 'Segoe UI', 'Microsoft YaHei';
                font-size: 11pt;
                padding: 8px 14px;
                text-align: left;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        header.addWidget(self.back_btn, 0)

        self.title_label = QLabel("工具")
        self.title_label.setStyleSheet("font-size: 24pt; font-weight: 300; margin-left: 12px;")
        header.addWidget(self.title_label)
        header.addStretch()
        root_layout.addLayout(header)

        self.container = QWidget()
        self.container.setStyleSheet("background-color: #202020; border: 1px solid #333; border-radius: 6px;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(16, 16, 16, 16)
        self.container_layout.setSpacing(0)
        root_layout.addWidget(self.container, 1)

    def set_tool_widget(self, widget: QWidget, title: str):
        clear_layout(self.container_layout)
        self.container_layout.addWidget(widget)
        self.title_label.setText(title)

    def clear(self):
        clear_layout(self.container_layout)
        self.title_label.setText("工具")
