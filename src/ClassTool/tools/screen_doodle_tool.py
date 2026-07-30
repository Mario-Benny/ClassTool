# -*- coding: utf-8 -*-

import ctypes
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from toolkit.core.tools_config import get_tool_config, set_tool_config


TOOL_INFO = {
    "name": "涂鸦模块",
    "color": "#5C2D91",
    "icon": "\uE790",
    "description": "屏幕冻结与三色批注",
    "requirements": ["PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"],
    "cache": True,
}

CONFIG_KEY = "screen_doodle"
TEMP_DIR_NAME = "class tool TMP"

PEN_COLORS = {
    "black": QColor("#111111"),
    "red": QColor("#E81123"),
    "blue": QColor("#0078D7"),
}


def _get_config() -> dict:
    config = get_tool_config(CONFIG_KEY)
    if isinstance(config, dict):
        return config
    return {}


def _save_config(**updates):
    config = _get_config()
    config.update(updates)
    try:
        set_tool_config(CONFIG_KEY, config)
    except OSError:
        pass


def _temp_dir() -> Path:
    path = Path(tempfile.gettempdir()) / TEMP_DIR_NAME
    path.mkdir(exist_ok=True)
    return path


def _force_topmost(widget: QWidget):
    if sys.platform != "win32" or not widget or not widget.isVisible():
        return
    try:
        hwnd = int(widget.winId())
        user32 = ctypes.windll.user32
        user32.SetWindowPos(
            hwnd,
            -1,  # HWND_TOPMOST
            0,
            0,
            0,
            0,
            0x0001 | 0x0002 | 0x0010 | 0x0040,  # NOSIZE | NOMOVE | NOACTIVATE | SHOWWINDOW
        )
    except Exception:
        pass


def _set_no_activate(widget: QWidget):
    """让悬浮球置顶但不抢 ClassTool 主窗口焦点。"""
    if sys.platform != "win32" or not widget:
        return
    try:
        hwnd = int(widget.winId())
        user32 = ctypes.windll.user32
        get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        ex_style = get_long(hwnd, -20)  # GWL_EXSTYLE
        set_long(hwnd, -20, ex_style | 0x08000000 | 0x00000080)  # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    except Exception:
        pass


def _window_flags():
    return (
        Qt.WindowType.Tool
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )


def _floating_ball_flags():
    return _window_flags() | Qt.WindowType.WindowDoesNotAcceptFocus


def _button_style(active=False, accent="#2f353b"):
    border = "#ffffff" if active else "#4b5560"
    return f"""
        QPushButton {{
            background-color: {accent};
            color: white;
            border: 1px solid {border};
            padding: 8px 12px;
            font-size: 11pt;
            font-weight: bold;
        }}
        QPushButton:hover {{ background-color: #3b434a; }}
        QPushButton:pressed {{ background-color: #24292e; }}
    """


class FloatingBall(QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(_floating_ball_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(66, 66)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.dragging = False
        self.drag_offset = QPoint()

        self.top_timer = QTimer(self)
        self.top_timer.setInterval(500)
        self.top_timer.timeout.connect(lambda: _force_topmost(self))

        self._place_on_left()

    def _place_on_left(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        saved_pos = _get_config().get("ball_pos")
        if isinstance(saved_pos, dict):
            x = saved_pos.get("x")
            y = saved_pos.get("y")
            if isinstance(x, int) and isinstance(y, int):
                max_x = geo.right() - self.width()
                max_y = geo.bottom() - self.height()
                self.move(
                    max(geo.left(), min(x, max_x)),
                    max(geo.top(), min(y, max_y)),
                )
                return
        self.move(geo.left() + 10, geo.top() + geo.height() // 2 - self.height() // 2)

    def show_ball(self):
        self._place_on_left()
        _set_no_activate(self)
        self.show()
        _set_no_activate(self)
        _force_topmost(self)
        self.top_timer.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QRadialGradient(22, 18, 56)
        gradient.setColorAt(0, QColor(255, 255, 255, 70))
        gradient.setColorAt(0.35, QColor(109, 74, 210, 238))
        gradient.setColorAt(1, QColor(42, 26, 102, 238))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 210), 2))
        painter.drawEllipse(4, 4, self.width() - 8, self.height() - 8)

        painter.setPen(QPen(QColor(255, 255, 255, 65), 1))
        painter.drawEllipse(10, 8, 24, 14)

        painter.setPen(QColor("white"))
        font = QFont("Microsoft YaHei UI", 20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "画")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            _force_topmost(self)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            _save_config(ball_pos={"x": self.x(), "y": self.y()})
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            _save_config(ball_pos={"x": self.x(), "y": self.y()})
            self.clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def closeEvent(self, event):
        self.top_timer.stop()
        super().closeEvent(event)


class DoodleOverlay(QWidget):
    exit_requested = Signal()

    def __init__(self, initial_color="red"):
        super().__init__(None)
        self.setWindowFlags(_window_flags())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.tool = "pen"
        self.pen_color_key = initial_color if initial_color in PEN_COLORS else "red"
        self.pen_width = 5
        self.eraser_width = 28
        self.is_drawing = False
        self.last_pos = QPoint()

        self.screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if self.screen is None:
            raise RuntimeError("无法获取屏幕信息")
        self.screen_geo = self.screen.geometry()
        self.background = self.screen.grabWindow(0)
        self.doodle_layer = QPixmap(self.background.size())
        self.doodle_layer.fill(Qt.GlobalColor.transparent)

        self.setGeometry(self.screen_geo)
        self._setup_toolbar()

        self.top_timer = QTimer(self)
        self.top_timer.setInterval(300)
        self.top_timer.timeout.connect(lambda: _force_topmost(self))

    def _setup_toolbar(self):
        self.toolbar = QFrame(self)
        self.toolbar.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 230);
                border: 1px solid rgba(255, 255, 255, 90);
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.black_btn = self._make_button("黑", lambda: self.set_pen("black"))
        self.red_btn = self._make_button("红", lambda: self.set_pen("red"))
        self.blue_btn = self._make_button("蓝", lambda: self.set_pen("blue"))
        self.eraser_btn = self._make_button("橡皮", self.set_eraser)
        self.clear_btn = self._make_button("清除", self.clear_doodle)
        self.exit_btn = self._make_button("×", self.exit_requested.emit, accent="#8b0000")

        for btn in (
            self.black_btn,
            self.red_btn,
            self.blue_btn,
            self.eraser_btn,
            self.clear_btn,
            self.exit_btn,
        ):
            layout.addWidget(btn)

        self._update_tool_buttons()
        self.toolbar.adjustSize()

    def _make_button(self, text, callback, accent="#2f353b"):
        btn = QPushButton(text)
        btn.setFixedHeight(38)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setStyleSheet(_button_style(accent=accent))
        btn.clicked.connect(callback)
        return btn

    def _place_toolbar(self):
        self.toolbar.adjustSize()
        margin = 20
        self.toolbar.move(margin, self.height() - self.toolbar.height() - margin)

    def _update_tool_buttons(self):
        self.black_btn.setStyleSheet(_button_style(self.tool == "pen" and self.pen_color_key == "black"))
        self.red_btn.setStyleSheet(_button_style(self.tool == "pen" and self.pen_color_key == "red"))
        self.blue_btn.setStyleSheet(_button_style(self.tool == "pen" and self.pen_color_key == "blue"))
        self.eraser_btn.setStyleSheet(_button_style(self.tool == "eraser"))
        self.clear_btn.setStyleSheet(_button_style())
        self.exit_btn.setStyleSheet(_button_style(accent="#8b0000"))

    def set_pen(self, color_key: str):
        if color_key in PEN_COLORS:
            self.tool = "pen"
            self.pen_color_key = color_key
            _save_config(pen_color=color_key)
            self._update_tool_buttons()

    def set_eraser(self):
        self.tool = "eraser"
        self._update_tool_buttons()

    def clear_doodle(self):
        self.doodle_layer.fill(Qt.GlobalColor.transparent)
        self.update()

    def show_overlay(self):
        _temp_dir()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._place_toolbar()
        _force_topmost(self)
        self.top_timer.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.background)
        painter.drawPixmap(0, 0, self.doodle_layer)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_toolbar()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.toolbar.geometry().contains(event.position().toPoint()):
            self.is_drawing = True
            self.last_pos = event.position().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            current_pos = event.position().toPoint()
            self._draw_line(self.last_pos, current_pos)
            self.last_pos = current_pos
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.exit_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _draw_line(self, start: QPoint, end: QPoint):
        painter = QPainter(self.doodle_layer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(Qt.GlobalColor.transparent, self.eraser_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            color = PEN_COLORS.get(self.pen_color_key, PEN_COLORS["red"])
            pen = QPen(color, self.pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.update()

    def closeEvent(self, event):
        self.top_timer.stop()
        super().closeEvent(event)


class DoodleManager:
    def __init__(self):
        self.ball = None
        self.overlay = None
        self.doodle_enabled = False

    def set_enabled(self, enabled: bool):
        self.doodle_enabled = bool(enabled)
        _save_config(enabled=self.doodle_enabled)
        if self.doodle_enabled:
            self.show_ball()
        else:
            self.shutdown()

    def show_ball(self):
        if self.ball is None:
            self.ball = FloatingBall()
            self.ball.clicked.connect(self.enter_doodle_mode)
        self.ball.show_ball()

    def enter_doodle_mode(self):
        if not self.doodle_enabled:
            return
        if self.ball is not None:
            self.ball.hide()
        self.exit_doodle_mode(show_ball=False)

        color = _get_config().get("pen_color", "red")
        self.overlay = DoodleOverlay(initial_color=color)
        self.overlay.exit_requested.connect(self.exit_doodle_mode)
        self.overlay.show_overlay()

    def exit_doodle_mode(self, show_ball=True):
        if self.overlay is not None:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None
        if show_ball and self.doodle_enabled:
            self.show_ball()

    def shutdown(self):
        self.exit_doodle_mode(show_ball=False)
        if self.ball is not None:
            self.ball.close()
            self.ball.deleteLater()
            self.ball = None


_manager = None


def get_manager() -> DoodleManager:
    global _manager
    if _manager is None:
        _manager = DoodleManager()
    return _manager


class DoodleSettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = get_manager()
        self._setup_ui()
        self._load_state()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #1e1e1e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title = QLabel("涂鸦模块")
        title.setStyleSheet("color: white; font-size: 22pt; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("开启后，屏幕左侧会出现悬浮球。点击悬浮球可冻结当前画面并进行三色批注。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cccccc; font-size: 11pt;")
        layout.addWidget(desc)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFixedHeight(56)
        self.toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self.toggle_btn)

        hint = QLabel("退出绘图模式：点击左下角 ×，或按 Esc。关闭悬浮球：回到这里关闭“涂鸦功能开启”。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8fa0ad; font-size: 10pt;")
        layout.addWidget(hint)

        layout.addStretch()

    def _load_state(self):
        enabled = bool(_get_config().get("enabled", False))
        self.toggle_btn.setChecked(enabled)
        self._refresh_button_text()
        if enabled:
            self.manager.set_enabled(True)
            QTimer.singleShot(0, self._restore_host_window)

    def _on_toggle(self, checked: bool):
        self.manager.set_enabled(checked)
        self._refresh_button_text()
        if checked:
            QTimer.singleShot(0, self._restore_host_window)

    def _restore_host_window(self):
        win = self.window()
        if win is not None:
            win.show()
            win.showNormal()
            win.raise_()
            win.activateWindow()

    def _refresh_button_text(self):
        if self.toggle_btn.isChecked():
            self.toggle_btn.setText("涂鸦功能开启：已开启")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #107C10;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16pt;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #168a16; }
            """)
        else:
            self.toggle_btn.setText("涂鸦功能开启：已关闭")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16pt;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #4a4a4a; }
            """)


def create_widget():
    return DoodleSettingsWidget()


def cleanup():
    if _manager is not None:
        _manager.shutdown()
