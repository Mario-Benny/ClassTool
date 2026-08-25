# -*- coding: utf-8 -*-

"""
工具运行时视图：显示工具标题和工具返回的 widget
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from toolkit.ui.utils import clear_layout


class ToolRuntimeView(QWidget):
    def __init__(self, translate, parent=None):
        super().__init__(parent)
        self._translate = translate
        self._tool_title = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 0)
        root_layout.setSpacing(10)

        header = QHBoxLayout()
        self.back_btn = QPushButton()
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

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: 600; margin-left: 12px;")
        header.addWidget(self.title_label)
        header.addStretch()
        root_layout.addLayout(header)

        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent; border: none;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        root_layout.addWidget(self.container, 1)
        self.retranslate_ui()

    def set_tool_widget(self, widget: QWidget, title: str):
        clear_layout(self.container_layout)
        self.container_layout.addWidget(widget)
        self._tool_title = title
        self.title_label.setText(title)

    def clear(self):
        clear_layout(self.container_layout)
        self._tool_title = None
        self.title_label.setText(self._translate("runtime.title"))

    def retranslate_ui(self):
        self.back_btn.setText(f"\uE72B {self._translate('runtime.back')}")
        if self._tool_title is None:
            self.title_label.setText(self._translate("runtime.title"))
