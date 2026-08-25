# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)

from toolkit.core.tools_config import get_tool_config, set_tool_config


TOOL_INFO = {
    "name": "倒计时装置",
    "color": "#FFB900",
    "icon": "\uE916",
    "description": "横向数字单元倒计时",
    "requirements": ["PySide6.QtCore", "PySide6.QtWidgets"],
    "cache": True,
}


CONFIG_KEY = "countdown_timer"
MAX_DIGIT = 9
DEFAULT_DIGITS = [0, 0, 0, 5, 0, 0]


def _load_digits() -> list[int]:
    config = get_tool_config(CONFIG_KEY)
    if isinstance(config, dict):
        digits = config.get("digits")
        if (
            isinstance(digits, list)
            and len(digits) == 6
            and all(isinstance(value, int) and 0 <= value <= MAX_DIGIT for value in digits)
        ):
            return list(digits)
    return list(DEFAULT_DIGITS)


def _save_digits(digits: list[int]):
    try:
        set_tool_config(CONFIG_KEY, {"digits": list(digits)})
    except OSError:
        pass


class DigitUnit(QWidget):
    def __init__(self, label: str, value: int, on_change, parent=None):
        super().__init__(parent)
        self._value = max(0, min(MAX_DIGIT, int(value)))
        self._on_change = on_change

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.plus_btn = QPushButton("+")
        self.plus_btn.clicked.connect(lambda: self.adjust(1))
        self.plus_btn.setFixedSize(58, 36)
        self.plus_btn.setStyleSheet(self._button_style())
        layout.addWidget(self.plus_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.digit_label = QLabel(str(self._value))
        self.digit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.digit_label.setFixedSize(78, 90)
        self.digit_label.setStyleSheet("""
            QLabel {
                background-color: #111418;
                color: #ffffff;
                border: 2px solid #333a42;
                border-radius: 8px;
                font-size: 42pt;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.digit_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.minus_btn = QPushButton("-")
        self.minus_btn.clicked.connect(lambda: self.adjust(-1))
        self.minus_btn.setFixedSize(58, 36)
        self.minus_btn.setStyleSheet(self._button_style())
        layout.addWidget(self.minus_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        name = QLabel(label)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        layout.addWidget(name)

    @staticmethod
    def _button_style() -> str:
        return """
            QPushButton {
                background-color: #2b3138;
                color: white;
                border: 1px solid #444c56;
                border-radius: 6px;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #38424c; }
            QPushButton:pressed { background-color: #20262d; }
            QPushButton:disabled {
                background-color: #1d2228;
                color: #5d6670;
                border-color: #2a3037;
            }
        """

    def value(self) -> int:
        return self._value

    def set_value(self, value: int):
        self._value = max(0, min(MAX_DIGIT, int(value)))
        self.digit_label.setText(str(self._value))

    def set_editable(self, editable: bool):
        self.plus_btn.setEnabled(editable)
        self.minus_btn.setEnabled(editable)

    def adjust(self, delta: int):
        self.set_value((self._value + delta) % 10)
        self._on_change()


class CountdownTimerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.digits = _load_digits()
        self.remaining_centiseconds = self._digits_to_centiseconds(self.digits)
        self.is_running = False
        self.has_finished = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

        self.units: list[DigitUnit] = []
        self._setup_ui()
        self._sync_units()
        self._refresh_state()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #101214;")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        title = QLabel("倒计时装置")
        title.setStyleSheet("color: white; font-size: 22pt; font-weight: bold;")
        root.addWidget(title)

        timer_row = QHBoxLayout()
        timer_row.setSpacing(10)
        timer_row.setContentsMargins(0, 10, 0, 8)
        timer_row.addStretch()

        labels = ["十时", "时", "十分", "分", "十秒", "秒"]
        for index, label in enumerate(labels):
            unit = DigitUnit(label, self.digits[index], self._on_digit_changed)
            self.units.append(unit)
            timer_row.addWidget(unit)
            if index in (1, 3):
                timer_row.addWidget(self._make_separator())

        timer_row.addStretch()
        root.addLayout(timer_row)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #d0d7de; font-size: 12pt;")
        root.addWidget(self.status_label)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addStretch()

        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.toggle_timer)
        self.start_btn.setFixedSize(120, 46)
        self.start_btn.setStyleSheet(self._control_style("#107C10", "#168a16"))
        controls.addWidget(self.start_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_timer)
        self.reset_btn.setFixedSize(120, 46)
        self.reset_btn.setStyleSheet(self._control_style("#2f353b", "#3b434a"))
        controls.addWidget(self.reset_btn)

        self.clear_btn = QPushButton("清零")
        self.clear_btn.clicked.connect(self.clear_timer)
        self.clear_btn.setFixedSize(120, 46)
        self.clear_btn.setStyleSheet(self._control_style("#8b0000", "#a11212"))
        controls.addWidget(self.clear_btn)

        controls.addStretch()
        root.addLayout(controls)
        root.addStretch()

    @staticmethod
    def _make_separator() -> QLabel:
        sep = QLabel(":")
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sep.setStyleSheet("color: #facc15; font-size: 46pt; font-weight: bold;")
        sep.setFixedWidth(22)
        return sep

    @staticmethod
    def _control_style(color: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: #1f1f1f; }}
            QPushButton:disabled {{
                background-color: #24292f;
                color: #6e7681;
            }}
        """

    @staticmethod
    def _digits_to_centiseconds(digits: list[int]) -> int:
        hours = digits[0] * 10 + digits[1]
        minutes = digits[2] * 10 + digits[3]
        seconds = digits[4] * 10 + digits[5]
        return ((hours * 100 + minutes) * 100 + seconds)

    @staticmethod
    def _centiseconds_to_digits(value: int) -> list[int]:
        value = max(0, min(999999, value))
        hours = value // 10000
        value %= 10000
        minutes = value // 100
        seconds = value % 100
        return [
            hours // 10,
            hours % 10,
            minutes // 10,
            minutes % 10,
            seconds // 10,
            seconds % 10,
        ]

    def _sync_units(self):
        for unit, value in zip(self.units, self.digits):
            unit.set_value(value)

    def _on_digit_changed(self):
        self.digits = [unit.value() for unit in self.units]
        self.remaining_centiseconds = self._digits_to_centiseconds(self.digits)
        self.has_finished = False
        _save_digits(self.digits)
        self._refresh_state()

    def _refresh_state(self):
        editable = not self.is_running
        for unit in self.units:
            unit.set_editable(editable)

        if self.has_finished:
            self.status_label.setText("时间到")
            self.start_btn.setEnabled(False)
        elif self.remaining_centiseconds <= 0:
            self.status_label.setText("请设置倒计时时间")
            self.start_btn.setEnabled(False)
        elif self.is_running:
            self.status_label.setText("倒计时进行中")
            self.start_btn.setEnabled(True)
        else:
            self.status_label.setText("可以单独调整每一位数字")
            self.start_btn.setEnabled(True)

        self.start_btn.setText("暂停" if self.is_running else "开始")

    def toggle_timer(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
        elif self.remaining_centiseconds > 0:
            self.is_running = True
            self.timer.start()
        self._refresh_state()

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.has_finished = False
        self.digits = _load_digits()
        self.remaining_centiseconds = self._digits_to_centiseconds(self.digits)
        self._sync_units()
        self._refresh_state()

    def clear_timer(self):
        self.timer.stop()
        self.is_running = False
        self.has_finished = False
        self.digits = [0, 0, 0, 0, 0, 0]
        self.remaining_centiseconds = 0
        _save_digits(self.digits)
        self._sync_units()
        self._refresh_state()

    def _tick(self):
        if self.remaining_centiseconds <= 0:
            self.timer.stop()
            self.is_running = False
            self._refresh_state()
            return

        self.remaining_centiseconds -= 1
        self.digits = self._centiseconds_to_digits(self.remaining_centiseconds)
        self._sync_units()

        if self.remaining_centiseconds <= 0:
            self.timer.stop()
            self.is_running = False
            self.has_finished = True
            self.status_label.setText("时间到")
        self._refresh_state()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def deleteLater(self):
        self.timer.stop()
        super().deleteLater()


def create_widget():
    return CountdownTimerWidget()
