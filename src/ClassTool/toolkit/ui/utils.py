# -*- coding: utf-8 -*-

"""
UI 通用小工具。
"""

from PySide6.QtWidgets import QLayout


def clear_layout(layout: QLayout, delete_widgets: bool = True):
    """清空布局；重排时可以只移除布局项而不销毁控件。"""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()

        if child_layout is not None:
            clear_layout(child_layout, delete_widgets)
        if widget is not None and delete_widgets:
            widget.deleteLater()
