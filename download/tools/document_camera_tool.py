# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QStackedWidget
)
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget

from toolkit.core.tools_config import get_tool_config, set_tool_config


TOOL_INFO = {
    "name": "展台",
    "color": "#107C10",
    "icon": "\uE722",
    "description": "自动搜索摄像头并实时展示画面",
    "requirements": [
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
    ],
    "cache": True,
}

CONFIG_KEY = "document_camera"

EXTERNAL_KEYWORDS = (
    "usb", "external", "capture", "hdmi", "uvc",
    "外置", "采集", "高拍", "展台"
)
INTERNAL_KEYWORDS = (
    "integrated", "internal", "built-in", "builtin", "laptop",
    "内置", "集成", "前置"
)


def _camera_id(device) -> str:
    raw = device.id()
    try:
        return bytes(raw).decode("utf-8", errors="ignore")
    except (TypeError, ValueError):
        return str(raw)


def _camera_name(device) -> str:
    name = device.description()
    return name if name else "摄像头"


def _camera_score(device, index: int) -> int:
    text = _camera_name(device).lower()
    score = index
    if any(keyword in text for keyword in EXTERNAL_KEYWORDS):
        score += 1000
    if any(keyword in text for keyword in INTERNAL_KEYWORDS):
        score -= 1000
    return score


def _load_saved_camera_id() -> str:
    config = get_tool_config(CONFIG_KEY)
    if isinstance(config, dict):
        value = config.get("camera_id")
        if isinstance(value, str):
            return value
    return ""


def _save_camera(device):
    try:
        set_tool_config(CONFIG_KEY, {
            "camera_id": _camera_id(device),
            "camera_name": _camera_name(device),
        })
    except OSError:
        pass


class DocumentCameraWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.devices = []
        self.camera = None
        self.session = QMediaCaptureSession(self)
        self.media_devices = QMediaDevices(self)

        self._setup_ui()
        self.media_devices.videoInputsChanged.connect(self.refresh_cameras)
        QTimer.singleShot(0, self.refresh_cameras)

    def _setup_ui(self):
        self.setStyleSheet("background-color: #101214;")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("展台")
        title.setStyleSheet("font-size: 20pt; color: white; font-weight: bold;")
        root.addWidget(title)

        self.display_stack = QStackedWidget()
        self.display_stack.setStyleSheet("background-color: #050607; border: 1px solid #2f353b;")

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #050607;")
        self.display_stack.addWidget(self.video_widget)

        self.message_label = QLabel("正在搜索摄像头...")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("color: #d0d7de; font-size: 22pt; background-color: #050607;")
        self.display_stack.addWidget(self.message_label)

        root.addWidget(self.display_stack, 1)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        switch_label = QLabel("切换摄像头")
        switch_label.setStyleSheet("color: #d0d7de; font-size: 11pt;")
        controls.addWidget(switch_label)

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(260)
        self.camera_combo.setStyleSheet("""
            QComboBox {
                background-color: #202428;
                color: white;
                border: 1px solid #3a4148;
                padding: 6px 10px;
                font-size: 11pt;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #202428;
                color: white;
                selection-background-color: #107C10;
            }
        """)
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        controls.addWidget(self.camera_combo)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedHeight(32)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2f353b;
                color: white;
                border: none;
                padding: 6px 14px;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #3b434a; }
            QPushButton:pressed { background-color: #24292e; }
        """)
        refresh_btn.clicked.connect(self.refresh_cameras)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        root.addLayout(controls)

    def refresh_cameras(self):
        try:
            self.devices = list(QMediaDevices.videoInputs())
        except Exception as exc:
            self.devices = []
            self.camera_combo.setEnabled(False)
            self._stop_camera()
            self._show_message(f"摄像头列表读取失败: {exc}")
            return

        self.camera_combo.blockSignals(True)
        try:
            self.camera_combo.clear()
            for device in self.devices:
                self.camera_combo.addItem(_camera_name(device), _camera_id(device))
        finally:
            self.camera_combo.blockSignals(False)

        if not self.devices:
            self._stop_camera()
            self.camera_combo.setEnabled(False)
            self._show_message("未找到摄像头")
            return

        self.camera_combo.setEnabled(True)
        selected_index = self._select_start_camera_index()
        self.camera_combo.setCurrentIndex(selected_index)
        self._start_camera(selected_index)

    def _select_start_camera_index(self) -> int:
        saved_id = _load_saved_camera_id()
        if saved_id:
            for index, device in enumerate(self.devices):
                if _camera_id(device) == saved_id:
                    return index

        ranked = sorted(
            enumerate(self.devices),
            key=lambda item: _camera_score(item[1], item[0]),
            reverse=True,
        )
        return ranked[0][0] if ranked else -1

    def _on_camera_changed(self, index: int):
        if 0 <= index < len(self.devices):
            self._start_camera(index)

    def _start_camera(self, index: int):
        if not 0 <= index < len(self.devices):
            self._show_message("未找到摄像头")
            return

        device = self.devices[index]
        self._stop_camera()

        try:
            self.camera = QCamera(device, self)
            self.camera.errorOccurred.connect(self._on_camera_error)
            self.session.setCamera(self.camera)
            self.session.setVideoOutput(self.video_widget)

            self._show_video()
            self.camera.start()
            _save_camera(device)
        except Exception as exc:
            self._stop_camera()
            self._show_message(f"摄像头打开失败: {exc}")

    def _stop_camera(self):
        if self.camera is not None:
            self.camera.stop()
            self.camera.deleteLater()
            self.camera = None
        try:
            self.session.setCamera(None)
        except RuntimeError:
            pass

    def _show_video(self):
        self.display_stack.setCurrentWidget(self.video_widget)

    def _show_message(self, message: str):
        self.message_label.setText(message)
        self.display_stack.setCurrentWidget(self.message_label)

    def _on_camera_error(self, error, error_string: str):
        message = error_string if error_string else "摄像头打开失败"
        self._show_message(message)

    def closeEvent(self, event):
        self._stop_camera()
        super().closeEvent(event)

    def hideEvent(self, event):
        super().hideEvent(event)

    def deleteLater(self):
        self._stop_camera()
        super().deleteLater()


def create_widget():
    return DocumentCameraWidget()
