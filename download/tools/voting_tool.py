# -*- coding: utf-8 -*-

"""课堂投票插件：配置投票位后打开可独立操作的投票窗口。"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


TOOL_INFO = {
    "name": "投票模块",
    "color": "#5C5C5C",
    "icon": "\uE8D4",
    "description": "创建独立投票页并实时计数",
    "requirements": ["PySide6.QtCore", "PySide6.QtWidgets"],
    "cache": True,
}


MIN_VOTE_SLOTS = 1
MAX_VOTE_SLOTS = 30
DEFAULT_VOTE_SLOTS = 5
VOTE_CELL_WIDTH = 176
VOTE_CELL_HEIGHT = 246
VOTE_CELL_GAP = 16

_active_vote_window = None


def _get_active_window():
    global _active_vote_window
    if _active_vote_window is not None and not _active_vote_window.isHidden():
        return _active_vote_window
    _active_vote_window = None
    return None


def _clear_active_window():
    global _active_vote_window
    _active_vote_window = None


class VoteCell(QFrame):
    """一个可改名、可上下调整票数的固定尺寸投票单元。"""

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._count = 0
        self.setFixedSize(VOTE_CELL_WIDTH, VOTE_CELL_HEIGHT)
        self.setObjectName("VoteCell")
        self.setStyleSheet("""
            QFrame#VoteCell {
                background-color: #3a3a3a;
                border: 1px solid #575757;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        self.name_input = QLineEdit(str(index))
        self.name_input.setMaxLength(24)
        self.name_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: white;
                border: none;
                border-bottom: 1px solid #707070;
                padding: 3px 0 6px;
                font-size: 14pt;
                font-weight: 600;
            }
            QLineEdit:focus { border-bottom-color: #4fa3ff; }
        """)
        layout.addWidget(self.name_input)
        layout.addStretch(1)

        self.plus_button = self._make_control_button("+")
        self.plus_button.setToolTip("增加一票")
        self.plus_button.clicked.connect(lambda: self._adjust_count(1))
        layout.addWidget(self.plus_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.count_label = QLabel("0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setFixedHeight(68)
        self.count_label.setMinimumWidth(118)
        self.count_label.setStyleSheet("""
            QLabel {
                background-color: #262626;
                color: white;
                border: 1px solid #606060;
                border-radius: 3px;
                font-size: 30pt;
                font-weight: 700;
            }
        """)
        layout.addWidget(self.count_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.minus_button = self._make_control_button("-")
        self.minus_button.setToolTip("减少一票")
        self.minus_button.clicked.connect(lambda: self._adjust_count(-1))
        layout.addWidget(self.minus_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

    @staticmethod
    def _make_control_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setFixedSize(118, 32)
        button.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                color: white;
                border: 1px solid #6a6a6a;
                border-radius: 3px;
                font-size: 16pt;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #626262; }
            QPushButton:pressed { background-color: #2c2c2c; }
        """)
        return button

    def _adjust_count(self, delta: int):
        self._count = max(0, self._count + delta)
        self.count_label.setText(str(self._count))


class VotingTitleBar(QWidget):
    """独立投票窗口的黑色标题栏和窗口控制按钮。"""

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self._parent_window = parent_window
        self._drag_offset = None
        self.setFixedHeight(42)
        self.setStyleSheet("background-color: #111111;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("投票")
        title.setStyleSheet("color: white; font-size: 12pt; font-weight: 600;")
        layout.addWidget(title)
        layout.addStretch()

        self.minimize_button = self._make_window_button("−", "最小化")
        self.minimize_button.clicked.connect(self._parent_window.showMinimized)
        layout.addWidget(self.minimize_button)

        self.fullscreen_button = self._make_window_button("□", "进入全屏")
        self.fullscreen_button.clicked.connect(self._parent_window.toggle_fullscreen)
        layout.addWidget(self.fullscreen_button)

        self.close_button = self._make_window_button("×", "关闭投票页", close_button=True)
        self.close_button.clicked.connect(self._parent_window.close)
        layout.addWidget(self.close_button)

    @staticmethod
    def _make_window_button(text: str, tooltip: str, close_button: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.setFixedSize(46, 42)
        hover_background = "#c42b1c" if close_button else "#333333"
        button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: white;
                border: none;
                font-size: 15pt;
            }}
            QPushButton:hover {{ background: {hover_background}; }}
        """)
        return button

    def set_fullscreen_state(self, is_fullscreen: bool):
        self.fullscreen_button.setText("❐" if is_fullscreen else "□")
        self.fullscreen_button.setToolTip("退出全屏" if is_fullscreen else "进入全屏")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._parent_window.isFullScreen():
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self._parent_window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            self._parent_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._parent_window.toggle_fullscreen()
            event.accept()


class VotingWindow(QWidget):
    """课堂展示用的独立投票页面。"""

    closed = Signal()

    def __init__(self, slot_count: int):
        super().__init__(None)
        self._cells: list[VoteCell] = []
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setWindowTitle("投票")
        self.resize(900, 620)
        self.setMinimumSize(520, 420)
        self.setStyleSheet("background-color: #101010;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = VotingTitleBar(self)
        root.addWidget(self.title_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: #101010;")

        self.cells_container = QWidget()
        self.cells_container.setStyleSheet("background-color: #101010;")
        self.cells_layout = QGridLayout(self.cells_container)
        self.cells_layout.setContentsMargins(28, 28, 28, 28)
        self.cells_layout.setSpacing(VOTE_CELL_GAP)
        self.cells_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.cells_container)
        root.addWidget(self.scroll_area, 1)

        for index in range(1, slot_count + 1):
            self._cells.append(VoteCell(index, self.cells_container))
        QTimer.singleShot(0, self._arrange_cells)

    def _arrange_cells(self):
        while self.cells_layout.count():
            self.cells_layout.takeAt(0)

        available_width = max(1, self.scroll_area.viewport().width() - 56)
        columns = max(1, (available_width + VOTE_CELL_GAP) // (VOTE_CELL_WIDTH + VOTE_CELL_GAP))
        for index, cell in enumerate(self._cells):
            self.cells_layout.addWidget(cell, index // columns, index % columns)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self.title_bar.set_fullscreen_state(self.isFullScreen())

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            self.title_bar.set_fullscreen_state(self.isFullScreen())
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_cells()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            self.title_bar.set_fullscreen_state(False)
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()


class VotingSetupWidget(QWidget):
    """主程序内的投票配置页。"""

    def __init__(self):
        super().__init__()
        self._vote_window = None
        self.setStyleSheet("background-color: #101214;")

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(20)

        title = QLabel("投票模块")
        title.setStyleSheet("color: white; font-size: 22pt; font-weight: 700;")
        root.addWidget(title)

        count_row = QHBoxLayout()
        label = QLabel("投票位数量")
        label.setStyleSheet("color: #d0d0d0; font-size: 12pt;")
        count_row.addWidget(label)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(MIN_VOTE_SLOTS, MAX_VOTE_SLOTS)
        self.count_spin.setValue(DEFAULT_VOTE_SLOTS)
        self.count_spin.setFixedWidth(108)
        self.count_spin.setStyleSheet("""
            QSpinBox {
                background-color: #303030;
                color: white;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13pt;
            }
        """)
        count_row.addWidget(self.count_spin)
        count_row.addStretch()
        root.addLayout(count_row)

        self.toggle_button = QPushButton()
        self.toggle_button.setFixedSize(168, 46)
        self.toggle_button.clicked.connect(self._toggle_voting_window)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12pt;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1788df; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        root.addWidget(self.toggle_button)
        root.addStretch()

        self._sync_window_state()

    def _toggle_voting_window(self):
        active_window = _get_active_window()
        if active_window is not None:
            active_window.close()
            return

        global _active_vote_window
        self._vote_window = VotingWindow(self.count_spin.value())
        _active_vote_window = self._vote_window
        self._vote_window.closed.connect(self._on_voting_window_closed)
        self._vote_window.show()
        self._vote_window.raise_()
        self._vote_window.activateWindow()
        self._sync_window_state()

    def _on_voting_window_closed(self):
        _clear_active_window()
        self._vote_window = None
        self._sync_window_state()

    def _sync_window_state(self):
        is_open = _get_active_window() is not None
        self.count_spin.setEnabled(not is_open)
        self.toggle_button.setText("关闭投票页" if is_open else "创建投票页")


def create_widget():
    return VotingSetupWidget()


def cleanup():
    """主程序退出时关闭仍在运行的投票窗口。"""
    active_window = _get_active_window()
    if active_window is not None:
        active_window.close()
