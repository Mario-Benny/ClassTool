# -*- coding: utf-8 -*-

"""
主窗口：组装组件，管理导航、主题、语言、托盘和插件列表。
"""

import os
from typing import Dict

from PySide6.QtCore import QFileSystemWatcher, QTimer, Qt
from PySide6.QtGui import QPixmap, QColor, QIcon, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSystemTrayIcon, QMenu, QMessageBox
)

from toolkit.core.plugin_loader import PluginLoader, PluginRuntimeError
from toolkit.core.theme_manager import ThemeManager
from toolkit.core.language_manager import LanguageManager
from toolkit.core.settings import get_setting, set_setting
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
        saved_theme = get_setting("theme", "dark")
        self.theme_manager = ThemeManager(
            saved_theme if saved_theme in ThemeManager.THEMES else "dark"
        )
        self.language_manager = LanguageManager()

        self.setWindowTitle(self.t("app.title"))
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.resize(1000, 700)

        self.loaded_plugins: Dict[str, dict] = {}
        self.nav_buttons = {}
        self.tile_widgets = []
        self._is_exiting = False

        self.setup_tray()
        self.setup_ui()
        self.language_manager.language_changed.connect(self.retranslate_ui)
        self.setup_watcher()
        self.refresh_tools()

        self.nav_buttons["home"].setChecked(True)
        self.on_nav_clicked("home")

    def t(self, key: str, **values: object) -> str:
        """返回主程序翻译文本。"""
        return self.language_manager.translate(key, **values)

    def set_language(self, language_code: str):
        self.language_manager.set_language(language_code)

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

        self.home_page = pages.create_home_page(self)
        self.settings_page = pages.create_settings_page(self)
        self.about_page = pages.create_about_page(self)
        self.tool_runtime_view = ToolRuntimeView(self.t)
        self.tool_runtime_view.back_btn.clicked.connect(self.back_to_home)

        self.content_stack.addWidget(self.home_page)
        self.content_stack.addWidget(self.settings_page)
        self.content_stack.addWidget(self.about_page)
        self.content_stack.addWidget(self.tool_runtime_view)

        nav_items = [
            ("home", "nav.home"),
            ("settings", "nav.settings"),
            ("about", "nav.about"),
        ]
        self._nav_translation_keys = {}
        for key, label_key in nav_items:
            btn = self.sidebar.add_nav_button(key, self.t(label_key))
            self.nav_buttons[key] = btn
            self._nav_translation_keys[key] = label_key
            btn.clicked.connect(lambda checked, k=key: self.on_nav_clicked(k))

        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_tools)

        self.apply_theme(self.theme_manager.current, persist=False)
        self.retranslate_ui()

    def retranslate_ui(self):
        """在不重建插件页面的前提下刷新主程序文本。"""
        self.setWindowTitle(self.t("app.title"))
        for key, label_key in self._nav_translation_keys.items():
            self.nav_buttons[key].set_text(self.t(label_key))
        pages.retranslate_home_page(self)
        pages.retranslate_settings_page(self)
        pages.retranslate_about_page(self)
        self.tool_runtime_view.retranslate_ui()
        self.show_action.setText(self.t("tray.show"))
        self.quit_action.setText(self.t("tray.exit"))

    # -------------------- 主题 --------------------
    def apply_theme(self, theme: str, persist: bool = True):
        self.theme_manager.set_theme(theme)
        if persist:
            set_setting("theme", self.theme_manager.current)
        self.setStyleSheet(self.theme_manager.get_global_style())

        colors = self.theme_manager.get_colors()
        self.sidebar.apply_theme(self.theme_manager.current, colors)
        self.title_bar.apply_theme(colors, self.theme_manager.current)
        pages.apply_page_theme(self)

    # -------------------- 导航 --------------------
    def on_nav_clicked(self, key: str):
        for nav_key, btn in self.nav_buttons.items():
            btn.setChecked(nav_key == key)

        page_map = {"home": 0, "settings": 1, "about": 2}
        if key in page_map:
            self.content_stack.setCurrentIndex(page_map[key])

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
        max_cols = min(3, max(1, (viewport_width + gap) // (tile_width + gap)))

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
            QMessageBox.warning(self, self.t("dialog.tool_load_title"), str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(
                self,
                self.t("dialog.tool_load_title"),
                self.t("dialog.tool_load_message", error=exc),
            )
            return

        widget = None
        try:
            if hasattr(module, "create_widget"):
                widget = module.create_widget()
            elif hasattr(module, "get_widget"):
                widget = module.get_widget()
        except Exception as exc:
            QMessageBox.critical(
                self,
                self.t("dialog.tool_load_title"),
                self.t("dialog.tool_page_message", error=exc),
            )
            return

        if widget is None:
            if hasattr(module, "run"):
                try:
                    module.run()
                except Exception as exc:
                    QMessageBox.critical(
                        self,
                        self.t("dialog.tool_run_title"),
                        self.t("dialog.tool_run_message", error=exc),
                    )
            return

        self.tool_runtime_view.set_tool_widget(widget, tool.get("name", tool_id))
        self.sidebar.hide()
        self.content_stack.setCurrentWidget(self.tool_runtime_view)

    def back_to_home(self):
        self.sidebar.show()
        self.content_stack.setCurrentIndex(0)
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == "home")

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

        self.tray_menu = QMenu()
        self.show_action = QAction(self.t("tray.show"), self)
        self.show_action.triggered.connect(self.show_and_raise)

        self.quit_action = QAction(self.t("tray.exit"), self)
        self.quit_action.triggered.connect(self.exit_app)

        self.tray_menu.addAction(self.show_action)
        self.tray_menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
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
