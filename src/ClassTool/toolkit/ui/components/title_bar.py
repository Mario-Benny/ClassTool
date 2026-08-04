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
        self.setFixedHeight(32)
        self.setStyleSheet("background-color: transparent;")
        self.drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        self.icon_label = QLabel("\uE71D")
        self.icon_label.setStyleSheet("font-family: 'Segoe MDL2 Assets'; font-size: 10pt; color: white; margin-right: 10px;")
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("ClassTool")
        self.title_label.setStyleSheet("font-size: 9pt; color: #ccc;")
        layout.addWidget(self.title_label)

        layout.addStretch()

        btn_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-family: 'Segoe MDL2 Assets';
                font-size: 10pt;
                width: 46px;
                height: 32px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
        """

        self.min_btn = QPushButton("\uE921")
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("\uE922")
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("\uE8BB")
        self.close_btn.setStyleSheet(btn_style + "QPushButton:hover { background-color: #e81123; }")
        self.close_btn.clicked.connect(lambda: self.window().close())
        layout.addWidget(self.close_btn)

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
