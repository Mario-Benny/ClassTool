# -*- coding: utf-8 -*-

"""
主题管理器：统一管理深色/浅色主题的色值和样式
"""

from typing import Dict, Any


class ThemeManager:
    """提供主题色值及全局样式表"""

    THEMES = {
        "dark": {
            "bg_main": "#1f1f1f",
            "bg_sidebar": "#2b2b2b",
            "bg_tool_runtime": "#202020",
            "border_main": "#333",
            "border_tool_runtime": "#333",
            "text_primary": "white",
            "text_secondary": "#cccccc",
            "text_title": "#e0e0e0",
            "scrollbar_handle": "#555",
            "scrollbar_handle_hover": "#777",
            "scrollbar_handle_pressed": "#999",
            "tile_default": "#2D89EF",
            "icon_color": "white",
        },
        "light": {
            "bg_main": "#f5f5f5",
            "bg_sidebar": "#ffffff",
            "bg_tool_runtime": "#ffffff",
            "border_main": "#d9d9d9",
            "border_tool_runtime": "#d0d0d0",
            "text_primary": "#1f1f1f",
            "text_secondary": "#4d4d4d",
            "text_title": "#4d4d4d",
            "scrollbar_handle": "#c9c9c9",
            "scrollbar_handle_hover": "#b5b5b5",
            "scrollbar_handle_pressed": "#9a9a9a",
            "tile_default": "#2D89EF",
            "icon_color": "#1f1f1f",
        }
    }

    def __init__(self, initial_theme="dark"):
        self._current = initial_theme

    @property
    def current(self) -> str:
        return self._current

    def set_theme(self, theme: str):
        if theme in self.THEMES:
            self._current = theme

    def get_colors(self) -> Dict[str, str]:
        """返回当前主题的所有颜色字典"""
        return self.THEMES.get(self._current, self.THEMES["dark"])

    def get_global_style(self) -> str:
        """生成全局样式表字符串"""
        c = self.get_colors()
        return f"""
            QMainWindow {{ background-color: {c["bg_main"]}; border: 1px solid {c["border_main"]}; }}
            QWidget#Sidebar {{ background-color: {c["bg_sidebar"]}; }}
            QLabel {{ color: {c["text_primary"]}; font-family: 'Segoe UI', 'Microsoft YaHei'; }}
            QScrollBar:vertical {{
                border: none; background-color: transparent; width: 12px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c["scrollbar_handle"]}; min-height: 20px; margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background-color: {c["scrollbar_handle_hover"]}; }}
            QScrollBar::handle:vertical:pressed {{ background-color: {c["scrollbar_handle_pressed"]}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{ background: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """