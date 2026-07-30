# -*- coding: utf-8 -*-

"""
主窗口：组装组件，管理导航、主题、托盘和插件列表。
"""

import os
from typing import Dict

from PySide6.QtCore import QFileSystemWatcher, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QIcon, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSystemTrayIcon, QMenu, QMessageBox
)

from toolkit.core.plugin_loader import PluginLoader, PluginRuntimeError
from toolkit.core.theme_manager import ThemeManager
from toolkit.ui.utils import clear_layout
from .components.title_bar import TitleBar
from .components.sidebar import Sidebar
from .components.metro_tile import MetroTile
from .components.tool_runtime_view import ToolRuntimeView
from . import pages


class MainWindow(QMainWindow):
    def __init__(self, plugin_loader: PluginLoader):
        super().__init__()
        self.plugin_loader = plugin_loader
        self.theme_manager = ThemeManager("dark")

        self.setWindowTitle("ClassTool")
        self.resize(1000, 700)

        self.sidebar_is_collapsed = False
        self.loaded_plugins: Dict[str, dict] = {}
        self.nav_buttons = {}
        self.tile_widgets = []
        self._is_exiting = False

        self.setup_tray()
        self.setup_ui()
        self.setup_watcher()
        self.refresh_tools()

        self.nav_buttons["tools"].setChecked(True)
        self.on_nav_clicked("tools")

    # -------------------- UI 构建 --------------------
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setSpacing(0)
        main_layout.addLayout(body)

        self.sidebar = Sidebar()
        body.addWidget(self.sidebar)

        self.content_stack = QStackedWidget()
        body.addWidget(self.content_stack)

        self.tools_page = pages.create_welcome_page(self)
        self.about_page = pages.create_about_page(self)
        self.tool_runtime_view = ToolRuntimeView()
        self.tool_runtime_view.back_btn.clicked.connect(self.back_to_tools)

        self.content_stack.addWidget(self.tools_page)
        self.content_stack.addWidget(self.about_page)
        self.content_stack.addWidget(self.tool_runtime_view)

        nav_items = [
            ("tools", "欢迎", "\uE71D"),
            ("about", "关于", "\uE946"),
        ]
        for key, label, icon in nav_items:
            btn = self.sidebar.add_nav_button(key, label, icon)
            self.nav_buttons[key] = btn
            btn.clicked.connect(lambda checked, k=key: self.on_nav_clicked(k))

        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.sidebar_animation.setDuration(250)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.sidebar_animation.valueChanged.connect(self._on_sidebar_width_changed)

        self.sidebar.hamburger_btn.clicked.connect(self.toggle_sidebar)

        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_tools)

        self.apply_theme(self.theme_manager.current)

    def _on_sidebar_width_changed(self, width: int):
        self.sidebar.setFixedWidth(width)
        is_narrow = width < 100
        for btn in self.nav_buttons.values():
            btn.set_collapsed(is_narrow)

    # -------------------- 主题 --------------------
    def apply_theme(self, theme: str):
        self.theme_manager.set_theme(theme)
        self.setStyleSheet(self.theme_manager.get_global_style())

        icon_color = self.theme_manager.get_colors()["icon_color"]
        for btn in self.nav_buttons.values():
            btn.icon_label.setStyleSheet(
                f"font-family: 'Segoe MDL2 Assets'; font-size: 12pt; "
                f"background: transparent; border: none; color: {icon_color};"
            )
            btn.update_style()

        hover_bg = "rgba(255, 255, 255, 0.1)" if theme == "dark" else "rgba(0, 0, 0, 0.06)"
        self.sidebar.hamburger_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {icon_color};
                font-family: 'Segoe MDL2 Assets';
                font-size: 12pt;
                text-align: center;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
        """)

        colors = self.theme_manager.get_colors()
        self.tool_runtime_view.container.setStyleSheet(
            f"background-color: {colors['bg_tool_runtime']}; "
            f"border: 1px solid {colors['border_tool_runtime']};"
        )
        self.title_bar.title_label.setStyleSheet(f"font-size: 9pt; color: {colors['text_title']};")

    # -------------------- 导航 --------------------
    def on_nav_clicked(self, key: str):
        for nav_key, btn in self.nav_buttons.items():
            btn.setChecked(nav_key == key)

        page_map = {"tools": 0, "about": 1}
        if key in page_map:
            self.content_stack.setCurrentIndex(page_map[key])

    # -------------------- 侧边栏折叠 --------------------
    def toggle_sidebar(self):
        start_width = self.sidebar.width()
        end_width = 60 if not self.sidebar_is_collapsed else 200
        self.sidebar_animation.setStartValue(start_width)
        self.sidebar_animation.setEndValue(end_width)
        self.sidebar_animation.start()
        self.sidebar_is_collapsed = not self.sidebar_is_collapsed

    # -------------------- 工具列表 --------------------
    def refresh_tools(self):
        clear_layout(self.tiles_layout)
        self.tile_widgets.clear()

        plugins = self.plugin_loader.load_plugins()
        self.loaded_plugins = {plugin["id"]: plugin for plugin in plugins}

        for tool in plugins:
            tile = MetroTile(
                tool["id"],
                tool.get("name", tool["id"]),
                color=tool.get("color", "#2D89EF"),
                icon_char=tool.get("icon"),
            )
            tile.clicked.connect(self.on_tool_clicked)
            self.tile_widgets.append(tile)

        self._rearrange_tiles()

    def _rearrange_tiles(self):
        if not hasattr(self, "tiles_layout"):
            return

        clear_layout(self.tiles_layout, delete_widgets=False)
        if not self.tile_widgets:
            return

        tile_width = 150
        gap = self.tiles_layout.spacing()
        viewport_width = self.scroll_area.viewport().width() if self.scroll_area else 800
        max_cols = max(1, (viewport_width + gap) // (tile_width + gap))

        row, col = 0, 0
        for tile in self.tile_widgets:
            self.tiles_layout.addWidget(tile, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    # -------------------- 工具运行 --------------------
    def on_tool_clicked(self, tool_id: str):
        tool = self.loaded_plugins.get(tool_id)
        if not tool:
            return

        try:
            module = self.plugin_loader.load_plugin_module(tool)
        except PluginRuntimeError as exc:
            QMessageBox.warning(self, "工具加载失败", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "工具加载失败", f"无法加载工具：{exc}")
            return

        widget = None
        try:
            if hasattr(module, "create_widget"):
                widget = module.create_widget()
            elif hasattr(module, "get_widget"):
                widget = module.get_widget()
        except Exception as exc:
            QMessageBox.critical(self, "工具加载失败", f"无法创建工具页面：{exc}")
            return

        if widget is None:
            if hasattr(module, "run"):
                try:
                    module.run()
                except Exception as exc:
                    QMessageBox.critical(self, "工具运行失败", f"工具运行异常：{exc}")
            return

        self.tool_runtime_view.set_tool_widget(widget, tool.get("name", tool_id))
        self.content_stack.setCurrentWidget(self.tool_runtime_view)

    def back_to_tools(self):
        self.content_stack.setCurrentIndex(0)
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == "tools")

    # -------------------- 文件监视器 --------------------
    def setup_watcher(self):
        tools_path = os.path.abspath(self.plugin_loader.tools_dir)
        self.watcher = QFileSystemWatcher([tools_path])
        self.watcher.directoryChanged.connect(self._on_directory_changed)

    def _on_directory_changed(self):
        self.refresh_timer.start(300)

    # -------------------- 托盘 --------------------
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        pm = QPixmap(24, 24)
        pm.fill(QColor("#0078d7"))
        self.tray_icon.setIcon(QIcon(pm))

        tray_menu = QMenu()
        show_action = QAction("显示主界面", self)
        show_action.triggered.connect(self.show_and_raise)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.exit_app)

        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def exit_app(self):
        if self._is_exiting:
            return
        self._is_exiting = True
        self._cleanup_before_exit()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _cleanup_before_exit(self):
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()
        if hasattr(self, "watcher"):
            self.watcher.removePaths(self.watcher.files() + self.watcher.directories())
        if hasattr(self, "tool_runtime_view"):
            self.tool_runtime_view.clear()

        cleanup_plugins = getattr(self.plugin_loader, "cleanup_plugins", None)
        if callable(cleanup_plugins):
            cleanup_plugins()

        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.showNormal()
        self.activateWindow()
        self.raise_()

    # -------------------- 窗口事件 --------------------
    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self.hide)
            event.ignore()
        super().changeEvent(event)

    def closeEvent(self, event):
        self._is_exiting = True
        self._cleanup_before_exit()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rearrange_tiles()
