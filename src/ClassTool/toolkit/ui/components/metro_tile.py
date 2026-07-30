# -*- coding: utf-8 -*-

"""
Metro 风格磁贴组件，使用 outline 避免悬停抖动
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class MetroTile(QFrame):
    clicked = Signal(str)

    def __init__(
        self,
        tool_id: str,
        name: str,
        color: str = "#0078D7",
        icon_char: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.tool_id = tool_id
        self.setFixedSize(150, 150)
        self.setObjectName("MetroTile")
        self.update_style(color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        if icon_char:
            self.icon_label = QLabel(icon_char)
            self.icon_label.setStyleSheet("""
                font-family: 'Segoe MDL2 Assets';
                font-size: 28pt;
                color: white;
                background: transparent;
            """)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.icon_label, 1)
        else:
            layout.addStretch(1)

        self.label = QLabel(name)
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 12pt; background: transparent;")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 增加轻微阴影效果（视觉优化）
        self.setGraphicsEffect(None)  # 不使用 QGraphicsDropShadowEffect 避免性能消耗，直接用样式

    def update_style(self, color: str):
        hover_color = QColor(color).lighter(120).name()
        # 使用 outline 避免尺寸变化
        self.setStyleSheet(f"""
            QFrame#MetroTile {{
                background-color: {color};
                border: none;
                border-radius: 6px;
                outline: 0px solid transparent;
            }}
            QFrame#MetroTile:hover {{
                background-color: {hover_color};
                outline: 2px solid rgba(255,255,255,0.6);
                outline-offset: -2px;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tool_id)
        super().mousePressEvent(event)