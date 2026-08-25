# -*- coding: utf-8 -*-

import ast
import operator

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout, QFrame

TOOL_INFO = {
    "name": "简易计算器",
    "color": "#E74856",
    "icon": "\uE8EF",
    "description": "手机计算器风格",
    "requirements": ["PySide6.QtCore", "PySide6.QtWidgets"],
    "cache": True,
}

MAX_EXPRESSION_LENGTH = 80
MAX_AST_NODES = 80
MAX_ABS_VALUE = 1_000_000_000_000
MAX_POWER_EXPONENT = 10

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _check_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("不支持的数字")
    if abs(value) > MAX_ABS_VALUE:
        raise ValueError("数值过大")
    return value


def _safe_power(left, right):
    if abs(right) > MAX_POWER_EXPONENT:
        raise ValueError("指数过大")
    return _check_number(operator.pow(left, right))


def safe_eval(expression: str):
    expression = expression.strip()
    if not expression:
        raise ValueError("表达式为空")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("表达式过长")

    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise ValueError("表达式过于复杂")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant):
            return _check_number(node.value)

        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Pow):
                return _safe_power(left, right)
            op = OPS.get(type(node.op))
            if op is None:
                raise ValueError("不支持的运算符")
            return _check_number(op(left, right))

        if isinstance(node, ast.UnaryOp):
            op = UNARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError("不支持的运算符")
            return _check_number(op(_eval(node.operand)))

        raise ValueError("不支持的表达式")

    return _eval(tree)


def _format_result(value):
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.12g}"
    return str(value)


class CalculatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.expression = {"text": ""}
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #0f1113;")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("计算器")
        title.setStyleSheet("font-size: 20pt; color: white;")
        layout.addWidget(title)

        display = QFrame()
        display.setStyleSheet("background-color: #171a1e; border: 1px solid #2c3138;")
        display_layout = QVBoxLayout(display)
        display_layout.setContentsMargins(14, 10, 14, 10)

        self.expr_label = QLabel("")
        self.expr_label.setStyleSheet("font-size: 12pt; color: #8fa0ad;")
        self.expr_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.result_label = QLabel("0")
        self.result_label.setStyleSheet("font-size: 28pt; color: white;")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        display_layout.addWidget(self.expr_label)
        display_layout.addWidget(self.result_label)
        layout.addWidget(display)

        pad = QGridLayout()
        pad.setSpacing(8)
        layout.addLayout(pad, 1)

        buttons = [
            ("C", self.clear_all, "#2f3540"), ("⌫", self.backspace, "#2f3540"), ("(", lambda: self.append_text("("), "#2f3540"), (")", lambda: self.append_text(")"), "#2f3540"),
            ("7", lambda: self.append_text("7"), "#1d232a"), ("8", lambda: self.append_text("8"), "#1d232a"), ("9", lambda: self.append_text("9"), "#1d232a"), ("÷", lambda: self.append_text("÷"), "#3d6cc7"),
            ("4", lambda: self.append_text("4"), "#1d232a"), ("5", lambda: self.append_text("5"), "#1d232a"), ("6", lambda: self.append_text("6"), "#1d232a"), ("×", lambda: self.append_text("×"), "#3d6cc7"),
            ("1", lambda: self.append_text("1"), "#1d232a"), ("2", lambda: self.append_text("2"), "#1d232a"), ("3", lambda: self.append_text("3"), "#1d232a"), ("-", lambda: self.append_text("-"), "#3d6cc7"),
            ("0", lambda: self.append_text("0"), "#1d232a"), (".", lambda: self.append_text("."), "#1d232a"), ("^", lambda: self.append_text("^"), "#1d232a"), ("+", lambda: self.append_text("+"), "#3d6cc7"),
        ]

        row = 0
        col = 0
        for text, callback, color in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(84, 58)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(f"background-color: {color}; color: white; border: none; font-size: 14pt;")
            btn.clicked.connect(callback)
            pad.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        equal_btn = QPushButton("=")
        equal_btn.setFixedHeight(58)
        equal_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        equal_btn.setStyleSheet("background-color: #0a84ff; color: white; border: none; font-size: 16pt;")
        equal_btn.clicked.connect(self.calculate)
        layout.addWidget(equal_btn)

    def append_text(self, text):
        if len(self.expression["text"]) + len(text) > MAX_EXPRESSION_LENGTH:
            self.result_label.setText("过长")
            return
        if self.result_label.text() in ("错误", "过长"):
            self.result_label.setText("0")
        self.expression["text"] += text
        self.expr_label.setText(self.expression["text"])

    def clear_all(self):
        self.expression["text"] = ""
        self.expr_label.setText("")
        self.result_label.setText("0")

    def backspace(self):
        self.expression["text"] = self.expression["text"][:-1]
        self.expr_label.setText(self.expression["text"])
        if not self.expression["text"]:
            self.result_label.setText("0")

    def calculate(self):
        expr = self.expression["text"].replace("×", "*").replace("÷", "/").replace("^", "**")
        if not expr.strip():
            return
        try:
            value = safe_eval(expr)
            result = _format_result(value)
            self.result_label.setText(result)
            self.expression["text"] = result
            self.expr_label.setText(self.expression["text"])
        except Exception:
            self.result_label.setText("错误")
            self.expression["text"] = ""
            self.expr_label.setText("")

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()

        if text in "0123456789.+-()^":
            self.append_text(text)
            event.accept()
            return
        if text == "*":
            self.append_text("×")
            event.accept()
            return
        if text == "/":
            self.append_text("÷")
            event.accept()
            return
        if text.lower() == "x":
            self.append_text("×")
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Equal):
            self.calculate()
            event.accept()
            return
        if key == Qt.Key.Key_Backspace:
            self.backspace()
            event.accept()
            return
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Escape):
            self.clear_all()
            event.accept()
            return

        super().keyPressEvent(event)


def create_widget():
    page = CalculatorWidget()
    page.setFocus()
    return page
