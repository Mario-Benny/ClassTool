# -*- coding: utf-8 -*-

"""首页、设置页和关于页的创建与翻译刷新。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGridLayout, QFrame, QComboBox, QPushButton, QCheckBox,
    QProgressBar
)

from toolkit.core.app_info import APP_VERSION, CHANGELOG_URL, GITHUB_URL, build_date
from .components.segmented_control import SegmentedControl


def create_home_page(main_window):
    """创建首页工具列表。"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)

    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(40, 40, 40, 40)

    title = QLabel()
    title.setStyleSheet("font-size: 28pt; font-weight: 300; margin-bottom: 20px;")
    container_layout.addWidget(title)

    # 为了保持与原有结构兼容，将 scroll_area 和 tiles_container 放在 main_window 中
    # 这里我们只返回容器，具体的 tile 网格由 main_window 管理
    # 所以我们把 scroll_area 的创建留在 main_window 中，但放在此页面内
    # 稍作调整：让 main_window 创建 scroll_area 然后添加到 page 中

    # 我们改为返回一个包含 scroll_area 的 page，但由 main_window 填充 tiles
    # 为了解耦，我们在 main_window 中保留对 scroll_area 的引用，并在此函数中创建
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setStyleSheet("background: transparent;")

    tiles_container = QWidget()
    tiles_layout = QGridLayout(tiles_container)
    tiles_layout.setSpacing(10)
    tiles_layout.setContentsMargins(0, 0, 0, 0)
    tiles_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    scroll_area.setWidget(tiles_container)
    container_layout.addWidget(scroll_area)

    layout.addWidget(container)

    # 将关键部件存到 main_window 中以便刷新
    main_window.scroll_area = scroll_area
    main_window.tiles_container = tiles_container
    main_window.tiles_layout = tiles_layout
    main_window.home_title = title
    retranslate_home_page(main_window)

    return page


def create_about_page(main_window):
    """创建关于页面。"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 40, 40, 40)

    title = QLabel()
    title.setStyleSheet("font-size: 28pt; font-weight: 300; margin-bottom: 20px;")
    layout.addWidget(title)

    info = QLabel()
    info.setStyleSheet("font-size: 12pt; line-height: 1.5;")
    layout.addWidget(info)

    links = QLabel()
    links.setOpenExternalLinks(True)
    links.setStyleSheet("font-size: 11pt; color: #d0eaff;")
    layout.addWidget(links)

    page.title_label = title
    page.info_label = info
    page.links_label = links
    main_window.about_page = page
    retranslate_about_page(main_window)

    layout.addStretch()
    return page


def create_settings_page(main_window):
    """创建主题、语言和本地设置管理页面。"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 40, 40, 40)
    layout.setSpacing(22)

    title = QLabel()
    title.setStyleSheet("font-size: 28pt; font-weight: 300; margin-bottom: 12px;")
    layout.addWidget(title)

    theme_label = QLabel()
    theme_label.setStyleSheet("font-size: 11pt;")
    theme_control = SegmentedControl()
    theme_control.value_changed.connect(main_window.apply_theme)
    theme_row = QHBoxLayout()
    theme_row.setSpacing(24)
    theme_row.addWidget(theme_label)
    theme_row.addWidget(theme_control)
    theme_row.addStretch()
    layout.addLayout(theme_row)

    language_label = QLabel()
    language_label.setStyleSheet("font-size: 11pt;")
    language_combo = QComboBox()
    language_combo.setFixedWidth(240)
    language_combo.setMaxVisibleItems(8)
    language_combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    language_row = QHBoxLayout()
    language_row.setSpacing(24)
    language_row.addWidget(language_label)
    language_row.addWidget(language_combo)
    language_row.addStretch()
    layout.addLayout(language_row)

    def on_language_change(index: int):
        language_code = language_combo.itemData(index)
        if language_code:
            main_window.set_language(language_code)

    language_combo.currentIndexChanged.connect(on_language_change)

    update_label = QLabel()
    update_label.setStyleSheet("font-size: 11pt; margin-top: 8px;")
    layout.addWidget(update_label)

    update_row = QHBoxLayout()
    update_row.setSpacing(10)
    auto_update_check = QCheckBox()
    auto_update_check.setChecked(main_window.auto_check_updates)
    auto_update_check.toggled.connect(main_window.set_auto_check_updates)
    check_update_btn = QPushButton()
    check_update_btn.setMinimumHeight(34)
    check_update_btn.clicked.connect(
        lambda: main_window.check_for_updates(manual=True)
    )
    update_row.addWidget(auto_update_check)
    update_row.addWidget(check_update_btn)
    update_row.addStretch()
    layout.addLayout(update_row)

    update_status = QLabel()
    update_progress = QProgressBar()
    update_progress.setRange(0, 100)
    update_progress.setTextVisible(False)
    update_progress.setFixedHeight(6)
    layout.addWidget(update_status)
    layout.addWidget(update_progress)

    data_label = QLabel()
    data_label.setStyleSheet("font-size: 11pt; margin-top: 8px;")
    layout.addWidget(data_label)

    data_actions = QHBoxLayout()
    data_actions.setSpacing(10)
    open_data_btn = QPushButton()
    export_btn = QPushButton()
    import_btn = QPushButton()
    reset_btn = QPushButton()
    for button in (open_data_btn, export_btn, import_btn, reset_btn):
        button.setMinimumHeight(34)
        data_actions.addWidget(button)
    data_actions.addStretch()
    layout.addLayout(data_actions)

    close_to_tray_check = QCheckBox()
    close_to_tray_check.setChecked(main_window.close_to_tray)
    close_to_tray_check.toggled.connect(main_window.set_close_to_tray)
    layout.addWidget(close_to_tray_check)

    context_menu_check = QCheckBox()
    context_menu_check.setChecked(main_window.context_menu_enabled)
    context_menu_check.toggled.connect(main_window.set_context_menu_enabled)
    layout.addWidget(context_menu_check)

    open_data_btn.clicked.connect(main_window.open_data_directory)
    export_btn.clicked.connect(main_window.export_settings)
    import_btn.clicked.connect(main_window.import_settings)
    reset_btn.clicked.connect(main_window.reset_app_settings)

    layout.addStretch()
    page.title_label = title
    page.theme_label = theme_label
    page.theme_control = theme_control
    page.language_label = language_label
    page.language_combo = language_combo
    page.update_label = update_label
    page.auto_update_check = auto_update_check
    page.check_update_btn = check_update_btn
    page.update_status = update_status
    page.update_progress = update_progress
    page.data_label = data_label
    page.open_data_btn = open_data_btn
    page.export_btn = export_btn
    page.import_btn = import_btn
    page.reset_btn = reset_btn
    page.close_to_tray_check = close_to_tray_check
    page.context_menu_check = context_menu_check
    main_window.settings_page = page
    retranslate_settings_page(main_window)
    return page


def retranslate_home_page(main_window):
    """刷新首页中属于主程序的文本。"""
    if hasattr(main_window, "home_title"):
        main_window.home_title.setText(main_window.t("home.title"))


def retranslate_about_page(main_window):
    """刷新关于页中属于主程序的文本。"""
    if not getattr(main_window, "about_page", None):
        return

    page = main_window.about_page
    translate = main_window.t
    page.title_label.setText(translate("about.title"))
    page.info_label.setText(
        "\n".join(
            (
                translate("about.version", version=APP_VERSION),
                translate("about.build_date", date=build_date()),
                translate("about.developer"),
                translate("about.framework"),
            )
        )
    )
    page.links_label.setText(
        f'{translate("about.bilibili")} '
        '<a href="https://space.bilibili.com/3706969464506745">'
        'https://space.bilibili.com/3706969464506745</a><br>'
        f'{translate("about.github")} '
        f'<a href="{GITHUB_URL}">{GITHUB_URL}</a><br>'
        f'{translate("about.changelog")} '
        f'<a href="{CHANGELOG_URL}">{CHANGELOG_URL}</a>'
    )



def retranslate_settings_page(main_window):
    """刷新设置页中的主题和语言选项。"""
    if not getattr(main_window, "settings_page", None):
        return

    page = main_window.settings_page
    translate = main_window.t
    page.title_label.setText(translate("settings.title"))
    page.theme_label.setText(translate("settings.theme"))
    page.theme_control.set_options(
        [
            ("dark", translate("theme.dark")),
            ("light", translate("theme.light")),
        ],
        main_window.theme_manager.current,
    )
    page.language_label.setText(translate("settings.language"))
    page.language_combo.blockSignals(True)
    page.language_combo.clear()
    for language_code, language_name in main_window.language_manager.available_languages():
        page.language_combo.addItem(language_name, language_code)
    page.language_combo.setCurrentIndex(
        page.language_combo.findData(main_window.language_manager.current_language)
    )
    page.language_combo.blockSignals(False)
    page.update_label.setText(translate("settings.update"))
    page.auto_update_check.blockSignals(True)
    page.auto_update_check.setText(translate("settings.auto_check_updates"))
    page.auto_update_check.setChecked(main_window.auto_check_updates)
    page.auto_update_check.blockSignals(False)
    page.check_update_btn.setText(translate("settings.check_updates"))
    update_update_controls(main_window)
    page.data_label.setText(translate("settings.data"))
    page.open_data_btn.setText(translate("settings.open_data"))
    page.export_btn.setText(translate("settings.export_settings"))
    page.import_btn.setText(translate("settings.import_settings"))
    page.reset_btn.setText(translate("settings.reset_settings"))
    page.close_to_tray_check.blockSignals(True)
    page.close_to_tray_check.setText(translate("settings.close_to_tray"))
    page.close_to_tray_check.setChecked(main_window.close_to_tray)
    page.close_to_tray_check.blockSignals(False)

    page.context_menu_check.blockSignals(True)
    page.context_menu_check.setText(translate("settings.context_menu"))
    page.context_menu_check.setChecked(main_window.context_menu_enabled)
    page.context_menu_check.blockSignals(False)


def update_update_controls(main_window):
    """只刷新更新状态和进度，避免下载时重建整张设置页。"""
    if not getattr(main_window, "settings_page", None):
        return

    page = main_window.settings_page
    page.update_status.setText(main_window.update_status_text())
    total = max(main_window.update_manager.total_bytes, 1)
    progress = min(100, int(main_window.update_manager.received_bytes * 100 / total))
    page.update_progress.setValue(progress)
    page.update_progress.setVisible(main_window.update_manager.state == "downloading")


def apply_page_theme(main_window):
    """让设置控件随主程序主题切换。"""
    if not getattr(main_window, "settings_page", None):
        return

    colors = main_window.theme_manager.get_colors()
    main_window.settings_page.theme_control.apply_theme(colors)
    selected_background = "#0078d7" if main_window.theme_manager.current == "dark" else "#0067b8"
    main_window.settings_page.language_combo.setStyleSheet(f"""
        QComboBox {{
            background: {colors['bg_sidebar']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_main']};
            border-radius: 4px;
            padding: 0 10px;
            font-size: 10pt;
            min-height: 32px;
        }}
        QComboBox:hover {{ border-color: {selected_background}; }}
        QComboBox::drop-down {{ border: none; width: 30px; }}
        QComboBox::down-arrow {{
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {colors['text_secondary']};
            margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{
            background: {colors['bg_sidebar']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_main']};
            selection-background-color: {selected_background};
            selection-color: white;
            outline: 0;
        }}
    """)
    main_window.settings_page.update_progress.setStyleSheet(f"""
        QProgressBar {{
            background: {colors['border_main']};
            border: none;
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background: {selected_background};
            border-radius: 3px;
        }}
    """)
    button_style = f"""
        QPushButton {{
            background: {colors['bg_sidebar']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_main']};
            border-radius: 4px;
            padding: 0 12px;
            font-size: 10pt;
        }}
        QPushButton:hover {{
            border-color: {selected_background};
            background: {selected_background};
            color: white;
        }}
        QPushButton:pressed {{ background: {colors['border_main']}; }}
    """
    for button in (
        main_window.settings_page.open_data_btn,
        main_window.settings_page.export_btn,
        main_window.settings_page.import_btn,
        main_window.settings_page.reset_btn,
    ):
        button.setStyleSheet(button_style)
    checkbox_style = f"""
        QCheckBox {{ color: {colors['text_primary']}; font-size: 10pt; spacing: 8px; }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['border_main']};
            background: {colors['bg_sidebar']};
        }}
        QCheckBox::indicator:checked {{
            background: {selected_background};
            border-color: {selected_background};
        }}
    """
    for checkbox in (
        main_window.settings_page.close_to_tray_check,
        main_window.settings_page.context_menu_check,
    ):
        checkbox.setStyleSheet(checkbox_style)
