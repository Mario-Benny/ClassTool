# -*- coding: utf-8 -*-

"""
自定义标题栏（包含窗口控制按钮、拖拽、双击最大化）
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication


class TitleBar(QWidget):
    """无边框窗口标题栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: transparent;")
        self.drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("ClassTool")
        self.title_label.setStyleSheet(
            "font-family: 'Segoe UI Variable Display', 'Segoe UI'; "
            "font-size: 15pt; font-weight: 700; color: #f2f2f2;"
        )
        layout.addWidget(self.title_label)

        layout.addStretch()

        self._button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                font-family: 'Segoe MDL2 Assets';
                font-size: 10pt;
                width: 46px;
                height: 40px;
            }
        """

        self.min_btn = QPushButton("\uE921")
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("\uE922")
        self.max_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("\uE8BB")
        self.close_btn.clicked.connect(lambda: self.window().close())
        layout.addWidget(self.close_btn)
        self.apply_theme({"text_title": "#f2f2f2", "text_primary": "white"}, "dark")

    def apply_theme(self, colors: dict[str, str], theme: str):
        """让文字标识与窗口按钮适配深浅主题。"""
        hover_background = "rgba(255, 255, 255, 0.1)" if theme == "dark" else "rgba(0, 0, 0, 0.06)"
        self.title_label.setStyleSheet(
            "font-family: 'Segoe UI Variable Display', 'Segoe UI'; "
            f"font-size: 15pt; font-weight: 700; color: {colors['text_title']};"
        )
        button_style = self._button_style + (
            f"QPushButton {{ color: {colors['text_primary']}; }}"
            f"QPushButton:hover {{ background-color: {hover_background}; }}"
        )
        self.min_btn.setStyleSheet(button_style)
        self.max_btn.setStyleSheet(button_style)
        self.close_btn.setStyleSheet(button_style + "QPushButton:hover { background-color: #e81123; color: white; }")

    def toggle_maximize(self):
        win = self.window()
        if not hasattr(self, "max_animation"):
            self.max_animation = QPropertyAnimation(win, b"geometry")
            self.max_animation.setDuration(250)
            self.max_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        if win.isMaximized():
            self.max_animation.stop()
            win.showNormal()
            self.max_btn.setText("\uE922")
        else:
            self.max_animation.stop()
            self.max_animation.setStartValue(win.geometry())
            screen = QApplication.screenAt(win.geometry().center())
            if not screen:
                screen = QApplication.primaryScreen()
            target_rect = screen.availableGeometry()
            self.max_animation.setEndValue(target_rect)

            def on_finished():
                if self.max_animation.endValue() == target_rect:
                    win.showMaximized()
                    self.max_btn.setText("\uE923")

            try:
                self.max_animation.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.max_animation.finished.connect(on_finished)
            self.max_animation.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.window().move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
