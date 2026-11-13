# -*- coding: utf-8 -*-

"""
主窗口：组装组件，管理导航、主题、语言、托盘和插件列表。
"""

import json
from pathlib import Path
from typing import Dict

from PySide6.QtCore import QFileSystemWatcher, QTimer, Qt, QUrl, QRect
from PySide6.QtGui import QPixmap, QColor, QIcon, QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QSystemTrayIcon, QMenu, QMessageBox, QFileDialog
)

from toolkit.core.app_info import APP_VERSION, CHANGELOG_URL, GITHUB_URL, build_date
from toolkit.core.app_logging import get_logger
from toolkit.core import context_menu
from toolkit.core.plugin_loader import PluginLoader, PluginRuntimeError
from toolkit.core.theme_manager import ThemeManager
from toolkit.core.language_manager import LanguageManager
from toolkit.core.paths import ensure_data_dir
from toolkit.core.safe_io import atomic_write_text, read_text_with_fallback
from toolkit.core.settings import (
    get_all_settings,
    get_setting,
    replace_settings,
    reset_settings,
    set_setting,
)
from toolkit.core.update_manager import UpdateManager
from toolkit.ui.utils import clear_layout
from .components.title_bar import TitleBar
from .components.sidebar import Sidebar
from .components.metro_tile import MetroTile
from .components.tool_runtime_view import ToolRuntimeView
from . import pages

_logger = get_logger("main_window")


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
        self.context_menu_enabled = bool(
            get_setting("context_menu_enabled", context_menu.DEFAULT_ENABLED)
        )
        self.auto_check_updates = bool(get_setting("auto_check_updates", True))
        self._manual_update_check = False
        self._prompted_update_version = ""

        self.setup_tray()
        self.setup_ui()
        self.language_manager.language_changed.connect(self.retranslate_ui)
        self._restore_window_state()
        self.setup_watcher()

        self.update_manager = UpdateManager(self)
        self.update_manager.state_changed.connect(self._on_update_state_changed)
        self.update_manager.download_progress.connect(self._on_update_progress)
        self.update_manager.update_ready.connect(self._on_update_ready)
        self.update_manager.no_update.connect(self._on_no_update)
        self.update_manager.error.connect(self._on_update_error)

        self.nav_buttons["home"].setChecked(True)
        self.on_nav_clicked("home")
        QTimer.singleShot(0, self.refresh_tools)
        QTimer.singleShot(10_000, self._start_auto_update_check)

    def t(self, key: str, **values: object) -> str:
        """返回主程序翻译文本。"""
        return self.language_manager.translate(key, **values)

    def set_language(self, language_code: str):
        self.language_manager.set_language(language_code)

    # -------------------- 软件更新 --------------------
    def set_auto_check_updates(self, enabled: bool):
        self.auto_check_updates = bool(enabled)
        set_setting("auto_check_updates", self.auto_check_updates)

    def _start_auto_update_check(self):
        if self.auto_check_updates and not self._is_exiting:
            self.check_for_updates(manual=False)

    def check_for_updates(self, manual: bool = True):
        if (
            manual
            and self.update_manager.state == "ready"
            and self.update_manager.ready_installer is not None
        ):
            self._prompted_update_version = ""
            self._on_update_ready(
                self.update_manager.latest_version,
                str(self.update_manager.ready_installer),
            )
            return
        self._manual_update_check = manual
        if not self.update_manager.check_for_updates(manual=manual) and manual:
            QMessageBox.information(
                self,
                self.t("update.title"),
                self.t("update.already_running"),
            )

    def _refresh_update_controls(self):
        if self.settings_page is not None:
            pages.update_update_controls(self)

    def _on_update_state_changed(self, _state: str):
        self._refresh_update_controls()

    def _on_update_progress(self, _received: int, _total: int):
        self._refresh_update_controls()

    def update_status_text(self) -> str:
        manager = self.update_manager
        if manager.state == "checking":
            return self.t("update.status_checking")
        if manager.state == "downloading":
            total = max(manager.total_bytes, 1)
            percent = min(100, int(manager.received_bytes * 100 / total))
            return self.t("update.status_downloading", percent=percent)
        if manager.state == "verifying":
            return self.t("update.status_verifying")
        if manager.state == "install_scheduled":
            return self.t("update.status_install_scheduled")
        if manager.state == "ready":
            return self.t("update.status_ready", version=manager.latest_version)
        if manager.state == "up_to_date":
            return self.t("update.status_current", version=APP_VERSION)
        if manager.state == "failed":
            return self.t("update.status_failed")
        return self.t("update.status_idle", version=APP_VERSION)

    def _on_no_update(self, version: str):
        if self._manual_update_check:
            QMessageBox.information(
                self,
                self.t("update.title"),
                self.t("update.no_update", version=version),
            )
        self._manual_update_check = False

    def _on_update_error(self, message: str):
        if self._manual_update_check:
            QMessageBox.warning(
                self,
                self.t("update.error_title"),
                self.t("update.error_message", error=message),
            )
        self._manual_update_check = False

    def _on_update_ready(self, version: str, _installer_path: str):
        repeat_prompt = self._manual_update_check
        if (
            version == self._prompted_update_version
            and not repeat_prompt
        ) or self._is_exiting:
            return
        self._prompted_update_version = version
        self._manual_update_check = False
        self.show_and_raise()

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setWindowTitle(self.t("update.ready_title"))
        dialog.setText(self.t("update.ready_message", version=version))
        install_button = dialog.addButton(
            self.t("update.install_now"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        dialog.addButton(
            self.t("update.install_later"),
            QMessageBox.ButtonRole.RejectRole,
        )
        dialog.exec()
        if dialog.clickedButton() is not install_button:
            return
        if not self.update_manager.schedule_install():
            QMessageBox.warning(
                self,
                self.t("update.error_title"),
                self.t("update.launch_failed"),
            )
            return
        self.exit_app()

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
        # 先取列表，成功后才清空重建：反过来的顺序一旦抛异常就留下一张永久空白首页。
        try:
            plugins = self.plugin_loader.load_plugins()
        except Exception:
            _logger.exception("工具列表刷新失败，保留当前列表")
            return

        self._ensure_watching()

        clear_layout(self.tiles_layout)
        self.tile_widgets.clear()

        self.loaded_plugins = {plugin["id"]: plugin for plugin in plugins}
        self._sync_context_menu(plugins)

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
            _logger.warning("插件加载失败 %s: %s", tool_id, exc)
            QMessageBox.warning(self, self.t("dialog.tool_load_title"), str(exc))
            return
        except Exception as exc:
            _logger.exception("插件加载出现未预期错误: %s", tool_id)
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
            _logger.exception("插件页面创建失败: %s", tool_id)
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
                    _logger.exception("插件运行失败: %s", tool_id)
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
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self._ensure_watching()

    def _ensure_watching(self):
        """重新注册被监视器丢弃的目录。

        目录被删除后 QFileSystemWatcher 会静默放弃该路径且永不自行恢复（实测：删除
        重建后目录不再出现在 directories() 中，此后增删插件毫无反应）。删除那一下
        仍能收到事件，所以把重注册挂在刷新路径上。但重建本身已无人通知，因此连父目录
        一起监视——tools 被重建时父目录会收到事件，覆盖安装与用户挪动目录都能自愈。
        """
        for watch_dir in self._watch_targets():
            path = str(watch_dir)
            if path not in self.watcher.directories():
                _logger.info("注册目录监视: %s", path)
                self.watcher.addPath(path)

    def _watch_targets(self):
        tools_dir = Path(self.plugin_loader.tools_dir)
        return [d for d in (tools_dir, tools_dir.parent) if d.is_dir()]

    def _on_directory_changed(self):
        self.refresh_timer.start(300)

    # -------------------- 设置与数据 --------------------
    def set_close_to_tray(self, enabled: bool):
        self.close_to_tray = bool(enabled)
        set_setting("close_to_tray", self.close_to_tray)

    # -------------------- 桌面右键菜单 --------------------
    def set_context_menu_enabled(self, enabled: bool, persist: bool = True):
        """设置页开关：开启时整棵重建，关闭时删掉本程序写入的子树。

        关闭时不判断注册表里是否真有菜单：用户可能用随包的 CMD 单独注册过，
        那不属于主程序的设置，主程序只清理自己按开关建出来的东西。
        """
        enabled = bool(enabled)
        previous = self.context_menu_enabled
        self.context_menu_enabled = enabled
        if persist:
            set_setting("context_menu_enabled", enabled)

        if enabled:
            self._sync_context_menu(self.loaded_plugins.values())
        elif previous:
            context_menu.unregister()

    def _sync_context_menu(self, tools):
        """插件列表变化后重新注册；关闭状态下不触碰注册表。"""
        if not self.context_menu_enabled:
            return
        entries = list(tools)
        if context_menu.register(entries):
            _logger.info("桌面右键菜单已更新: %d 项", len(entries))

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
            atomic_write_text(
                path,
                json.dumps(get_all_settings(), ensure_ascii=False, indent=2),
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
            payload = json.loads(read_text_with_fallback(Path(filename)))
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
        self.auto_check_updates = bool(get_setting("auto_check_updates", True))
        self.set_context_menu_enabled(
            bool(get_setting("context_menu_enabled", context_menu.DEFAULT_ENABLED)),
            persist=False,
        )
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
        try:
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
        except OSError as exc:
            # 写设置失败不能拦住退出流程，否则托盘"退出"点下去毫无反应。
            _logger.warning("窗口状态保存失败: %s", exc)

    # -------------------- 托盘 --------------------
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
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
        if self.tray_available:
            self.tray_icon.show()
        else:
            _logger.warning("系统托盘当前不可用，关闭窗口时将直接退出")

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
        if hasattr(self, "update_manager"):
            self.update_manager.shutdown()
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
        was_maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)
        self.show()
        if was_maximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.activateWindow()
        self.raise_()

    # -------------------- 窗口事件 --------------------
    def changeEvent(self, event):
        if (
            event.type() == event.Type.WindowStateChange
            and self.isMinimized()
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            QTimer.singleShot(0, self.hide)
            event.ignore()
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.sync_window_state()

    def closeEvent(self, event):
        if (
            self.close_to_tray
            and not self._is_exiting
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
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
