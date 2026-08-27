# -*- coding: utf-8 -*-

"""
主窗口：组装组件，管理导航、主题、语言、托盘和插件列表。
"""

import json
import os
from pathlib import Path
from typing import Dict

from PySide6.QtCore import QFileSystemWatcher, QTimer, Qt, QUrl, QRect
from PySide6.QtGui import QPixmap, QColor, QIcon, QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSystemTrayIcon, QMenu, QMessageBox, QFileDialog
)

from toolkit.core.app_info import APP_VERSION, CHANGELOG_URL, GITHUB_URL, build_date
from toolkit.core.plugin_loader import PluginLoader, PluginRuntimeError
from toolkit.core.theme_manager import ThemeManager
from toolkit.core.language_manager import LanguageManager
from toolkit.core.paths import ensure_data_dir
from toolkit.core.settings import (
    get_all_settings,
    get_setting,
    replace_settings,
    reset_settings,
    set_setting,
)
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
        self.close_to_tray = bool(get_setting("close_to_tray", False))

        self.setup_tray()
        self.setup_ui()
        self.language_manager.language_changed.connect(self.retranslate_ui)
        self._restore_window_state()
        self.setup_watcher()

        self.nav_buttons["home"].setChecked(True)
        self.on_nav_clicked("home")
        QTimer.singleShot(0, self.refresh_tools)

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
        self.settings_page = None
        self.about_page = None
        self.tool_runtime_view = ToolRuntimeView(self.t)
        self.tool_runtime_view.back_btn.clicked.connect(self.back_to_home)

        self.content_stack.addWidget(self.home_page)
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

        if key == "home":
            self.content_stack.setCurrentWidget(self.home_page)
        elif key == "settings":
            self.content_stack.setCurrentWidget(self._ensure_settings_page())
        elif key == "about":
            self.content_stack.setCurrentWidget(self._ensure_about_page())

    def _ensure_settings_page(self):
        if self.settings_page is None:
            self.settings_page = pages.create_settings_page(self)
            self.content_stack.addWidget(self.settings_page)
            pages.apply_page_theme(self)
        return self.settings_page

    def _ensure_about_page(self):
        if self.about_page is None:
            self.about_page = pages.create_about_page(self)
            self.content_stack.addWidget(self.about_page)
        return self.about_page

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

    # -------------------- 设置与数据 --------------------
    def set_close_to_tray(self, enabled: bool):
        self.close_to_tray = bool(enabled)
        set_setting("close_to_tray", self.close_to_tray)

    def open_data_directory(self):
        data_dir = ensure_data_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir)))

    def export_settings(self):
        self._save_window_state()
        default_path = ensure_data_dir() / "classtool-settings.json"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.t("settings.export_settings"),
            str(default_path),
            "JSON (*.json)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        try:
            path.write_text(
                json.dumps(get_all_settings(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                self.t("settings.export_failed_title"),
                self.t("settings.export_failed_message", error=exc),
            )

    def import_settings(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.t("settings.import_settings"),
            str(ensure_data_dir()),
            "JSON (*.json)",
        )
        if not filename:
            return
        try:
            payload = json.loads(Path(filename).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(self.t("settings.invalid_file"))
            replace_settings(payload)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(
                self,
                self.t("settings.import_failed_title"),
                self.t("settings.import_failed_message", error=exc),
            )
            return
        self._apply_saved_preferences()

    def reset_app_settings(self):
        answer = QMessageBox.question(
            self,
            self.t("settings.reset_settings"),
            self.t("settings.reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        reset_settings()
        self._apply_saved_preferences()

    def _apply_saved_preferences(self):
        saved_theme = get_setting("theme", "dark")
        self.apply_theme(
            saved_theme if saved_theme in ThemeManager.THEMES else "dark",
            persist=False,
        )
        language_code = get_setting("language", LanguageManager.DEFAULT_LANGUAGE)
        self.language_manager.set_language(language_code)
        self.close_to_tray = bool(get_setting("close_to_tray", False))
        self.retranslate_ui()

    # -------------------- 窗口状态 --------------------
    @staticmethod
    def _setting_int(value, default: int) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    def _restore_window_state(self):
        state = get_setting("window_state", {})
        if not isinstance(state, dict):
            return

        geometry = self.geometry()
        width = max(720, self._setting_int(state.get("width"), geometry.width()))
        height = max(520, self._setting_int(state.get("height"), geometry.height()))
        restored = QRect(
            self._setting_int(state.get("x"), geometry.x()),
            self._setting_int(state.get("y"), geometry.y()),
            width,
            height,
        )
        screens = QApplication.screens()
        if screens and not any(screen.availableGeometry().intersects(restored) for screen in screens):
            available = QApplication.primaryScreen().availableGeometry()
            restored.moveCenter(available.center())
        self.setGeometry(restored)

        if bool(state.get("maximized", False)):
            QTimer.singleShot(0, self._restore_maximized_window)

    def _restore_maximized_window(self):
        self.showMaximized()
        self.title_bar.sync_window_state()

    def _save_window_state(self):
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        if not geometry.isValid():
            geometry = self.geometry()
        set_setting(
            "window_state",
            {
                "x": geometry.x(),
                "y": geometry.y(),
                "width": geometry.width(),
                "height": geometry.height(),
                "maximized": self.isMaximized(),
            },
        )

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
        self._save_window_state()
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
        if event.type() == event.Type.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.sync_window_state()

    def closeEvent(self, event):
        if self.close_to_tray and not self._is_exiting:
            self._save_window_state()
            self.hide()
            event.ignore()
            return
        self._is_exiting = True
        self._save_window_state()
        self._cleanup_before_exit()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rearrange_tiles()
