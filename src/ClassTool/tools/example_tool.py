# -*- coding: utf-8 -*-

"""Minimal ClassTool plugin template for developers."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from toolkit.core.tools_config import get_tool_config, set_tool_config


TOOL_INFO = {
    "name": "Example Tool",
    "color": "#2D89EF",
    "icon": "\uECAA",
    "description": "A minimal plugin template for ClassTool.",
    "requirements": ["PySide6.QtCore", "PySide6.QtWidgets"],
    "cache": True,
}


def create_widget():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(16)

    count = int(get_tool_config("example_tool_count") or 0)
    label = QLabel(f"Button clicked {count} time(s).")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet("font-size: 18pt;")

    button = QPushButton("Click")
    button.setMinimumHeight(40)

    def on_click():
        nonlocal count
        count += 1
        set_tool_config("example_tool_count", count)
        label.setText(f"Button clicked {count} time(s).")

    button.clicked.connect(on_click)

    layout.addStretch(1)
    layout.addWidget(label)
    layout.addWidget(button)
    layout.addStretch(1)
    return page


def cleanup():
    """Release resources here if the plugin starts threads, timers, or devices."""
