# -*- coding: utf-8 -*-

"""
所有页面（欢迎页、关于页）的工厂方法
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGridLayout, QFrame, QComboBox
)


def create_welcome_page(main_window):
    """工具列表页（实际是欢迎页）"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)

    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(40, 40, 40, 40)

    title = QLabel("欢迎使用 ClassTool 课堂工具集")
    title.setStyleSheet("font-size: 28pt; font-weight: 300; margin-bottom: 20px;")
    container_layout.addWidget(title)

    # 为了保持与原有结构兼容，将 scroll_area 和 tiles_container 放在 main_window 中
    # 这里我们只返回容器，具体的 tile 网格由 main_window 管理
    # 所以我们把 scroll_area 的创建留在 main_window 中，但放在此页面内
    # 稍作调整：让 main_window 创建 scroll_area 然后添加到 page 中

    # 我们改为返回一个包含 scroll_area 的 page，但由 main_window 填充 tiles
    # 为了解耦，我们在 main_window 中保留对 scroll_area 的引用，并在此函数中创建
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setStyleSheet("background: transparent;")

    tiles_container = QWidget()
    tiles_layout = QGridLayout(tiles_container)
    tiles_layout.setSpacing(10)
    tiles_layout.setContentsMargins(0, 0, 0, 0)
    tiles_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    scroll_area.setWidget(tiles_container)
    container_layout.addWidget(scroll_area)

    layout.addWidget(container)

    # 将关键部件存到 main_window 中以便刷新
    main_window.scroll_area = scroll_area
    main_window.tiles_container = tiles_container
    main_window.tiles_layout = tiles_layout

    return page


def create_about_page(main_window):
    """关于页面，包含主题切换"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 40, 40, 40)

    title = QLabel("关于 ClassToolkit")
    title.setStyleSheet("font-size: 28pt; font-weight: 300; margin-bottom: 20px;")
    layout.addWidget(title)

    info = QLabel(
        "版本: 1.0.2\n"
        "开发者: Mario_YU\n"
        "基于 PySide6 构建"
    )
    info.setStyleSheet("font-size: 12pt; line-height: 1.5;")
    layout.addWidget(info)

    links = QLabel(
        'B站主页：<a href="https://space.bilibili.com/3706969464506745">'
        'https://space.bilibili.com/3706969464506745</a><br>'
        'GitHub 主页：<a href="https://github.com/Yu-Mario">'
        'https://github.com/Yu-Mario</a>'
    )
    links.setOpenExternalLinks(True)
    links.setStyleSheet("font-size: 11pt; color: #d0eaff;")
    layout.addWidget(links)

    # 主题切换下拉框
    theme_row = QHBoxLayout()
    theme_label = QLabel("主题")
    theme_label.setStyleSheet("font-size: 11pt;")
    theme_combo = QComboBox()
    theme_combo.addItems(["深色", "浅色"])
    theme_combo.setCurrentIndex(0 if main_window.theme_manager.current == "dark" else 1)
    theme_combo.setStyleSheet("font-size: 11pt; padding: 4px;")
    theme_row.addWidget(theme_label)
    theme_row.addWidget(theme_combo)
    theme_row.addStretch()
    layout.addLayout(theme_row)

    def on_theme_change(idx: int):
        theme = "dark" if idx == 0 else "light"
        main_window.apply_theme(theme)

    theme_combo.currentIndexChanged.connect(on_theme_change)

    layout.addStretch()
    return page
