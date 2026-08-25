# -*- coding: utf-8 -*-

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox
)

from toolkit.core.tools_config import get_tool_config, set_tool_config

TOOL_INFO = {
    "name": "随机点名器",
    "color": "#0078D7",
    "icon": "\uE716",
    "description": "输入学号上限，每次抽取不重复",
    "requirements": ["PySide6.QtCore", "PySide6.QtWidgets"],
    "cache": True,
}

DEFAULT_MAX_NUMBER = 36
CONFIG_KEY = "random_picker"


def _load_saved_max_number():
    config = get_tool_config(CONFIG_KEY)
    if isinstance(config, dict):
        value = config.get("max_number")
        if isinstance(value, int) and 1 <= value <= 999:
            return value
    return DEFAULT_MAX_NUMBER


def _save_max_number(value: int):
    if isinstance(value, int) and 1 <= value <= 999:
        try:
            set_tool_config(CONFIG_KEY, {"max_number": value})
        except OSError:
            pass


def create_widget():
    page = QWidget()
    page.setStyleSheet("background-color: #1e1e1e;")
    
    layout = QVBoxLayout(page)
    layout.setSpacing(20)
    layout.setContentsMargins(30, 30, 30, 30)

    # 标题
    title = QLabel("🎲 随机点名器")
    title.setStyleSheet("color: #ffffff; font-size: 22pt; font-weight: bold;")
    layout.addWidget(title)

    # 输入上限
    input_layout = QHBoxLayout()
    label = QLabel("学号上限：")
    label.setStyleSheet("color: #cccccc; font-size: 12pt;")
    input_layout.addWidget(label)

    spin = QSpinBox()
    spin.setRange(1, 999)
    spin.setValue(_load_saved_max_number())
    spin.setFixedWidth(100)
    spin.setStyleSheet("color: #ffffff; background-color: #333333; font-size: 14pt;")
    input_layout.addWidget(spin)
    input_layout.addStretch()
    layout.addLayout(input_layout)

    # 结果显示（超大亮色）
    result_label = QLabel("?")
    result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    result_label.setStyleSheet("color: #4FC3F7; font-size: 80pt; font-weight: bold;")
    layout.addWidget(result_label)

    # 按钮
    btn = QPushButton("开始抽取")
    btn.setFixedHeight(60)
    btn.setStyleSheet("""
        QPushButton {
            background-color: #0078D7;
            color: white;
            font-size: 18pt;
            font-weight: bold;
            border: none;
            border-radius: 8px;
        }
        QPushButton:hover {
            background-color: #1E88E5;
        }
        QPushButton:pressed {
            background-color: #005A9E;
        }
    """)
    layout.addWidget(btn)

    # ========== 核心逻辑 ==========
    last_picked = None   # 上一次抽到的学号

    def draw():
        nonlocal last_picked
        max_num = spin.value()
        
        candidates = list(range(1, max_num + 1))
        if last_picked is not None and len(candidates) > 1:
            try:
                candidates.remove(last_picked)
            except ValueError:
                pass
        
        # 随机选一个
        picked = random.choice(candidates)
        result_label.setText(str(picked))
        
        # 记录本次抽到的，供下次排除
        last_picked = picked
        
        # 按钮文字首次点击后永久变为“继续抽取”
        if btn.text() == "开始抽取":
            btn.setText("继续抽取")

    def on_btn_click():
        draw()

    btn.clicked.connect(on_btn_click)

    # 修改上限时重置状态
    def on_spin_changed(value):
        nonlocal last_picked
        _save_max_number(value)
        last_picked = None
        result_label.setText("?")
        btn.setText("开始抽取")
    spin.valueChanged.connect(on_spin_changed)
    _save_max_number(spin.value())

    # 初始化
    result_label.setText("?")
    btn.setText("开始抽取")

    return page
