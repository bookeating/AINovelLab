#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Material Design 风格的样式定义 - 暗色调版本
"""

def get_material_style():
    """返回 Material Design 风格的暗色调样式表"""
    # 定义颜色变量 - 暗色调方案
    primary_color = "#5C6BC0"  # 靛蓝作为主色调，但更加柔和
    primary_dark_color = "#3949AB"
    primary_light_color = "#C5CAE9"
    accent_color = "#7986CB"  # 使用更和谐的蓝紫色作为强调色
    accent_dark_color = "#5C6BC0"
    background_color = "#1A1A1A"  # 更深的背景色
    card_background = "#2D2D2D"  # 卡片背景稍微浅一些
    text_primary = "#FFFFFF"
    text_secondary = "#B0B0B0"
    divider_color = "#333333"
    surface_color = "#252525"
    frame_color = "#383838"
    
    # 完整的样式表
    return """
    /* ======== 全局样式 ======== */
    QWidget {
        font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
        font-size: 13px;
        color: """ + text_primary + """;
        background-color: """ + background_color + """;
    }
    
    /* ======== 主窗口样式 ======== */
    QMainWindow {
        background-color: """ + background_color + """;
        border: none;
    }
    
    /* ======== 标签页样式 ======== */
    QTabWidget::pane {
        border: 1px solid """ + divider_color + """;
        border-top: none;  /* 移除顶部边框 */
        background-color: """ + background_color + """;
        border-radius: 0px;
        top: 0px;  /* 调整位置对齐标签栏 */
        margin-top: -1px;  /* 略微上移，覆盖底部线 */
    }
    
    /* 移除标签栏底部线 */
    QTabBar::tab-bar {
        left: 0px;
        border: none;
        background-color: """ + background_color + """;
    }
    
    QTabWidget {
        /* 允许标签栏自由拉伸 */
        qproperty-documentMode: true;  /* 使用更简洁的文档模式 */
        qproperty-tabsClosable: false;
        qproperty-movable: false;
        qproperty-elideMode: 0;  /* 不省略文本 */
        qproperty-usesScrollButtons: true;  /* 启用滚动按钮 */
        border: none;  /* 完全移除边框 */
        background-color: """ + background_color + """;
    }
    
    /* 选项卡区域无边框 */
    QTabWidget::tab-bar {
        border: none;
        background-color: """ + background_color + """;
    }
    
    QTabBar {
        alignment: left;  /* 标签左对齐 */
        /* 允许标签栏自由拉伸 */
        qproperty-expanding: false;  /* 不自动拉伸，保持实际大小 */
        qproperty-usesScrollButtons: true;
        qproperty-elideMode: 0;  /* 不省略文本 */
        border: none; /* 确保没有边框 */
        background-color: """ + background_color + """;
    }
    
    /* 移除标签的外部轮廓线 */
    QTabBar::tab {
        padding: 6px 15px;  /* 再增加水平padding，确保有足够空间 */
        background-color: """ + background_color + """;
        border: none; /* 移除所有边框 */
        border-bottom: 2px solid transparent;
        margin-right: 2px;  /* 减少标签间距，更紧凑 */
        font-weight: normal;
        color: """ + text_secondary + """;
        font-size: 13px;
        min-width: 100px;  /* 确保每个标签有足够宽度 */
        text-align: center;  /* 文本居中 */
    }
    
    QTabBar::tab:selected {
        color: """ + accent_color + """;
        border-bottom: 2px solid """ + accent_color + """;
        font-weight: bold;
        background-color: """ + background_color + """;
        border-bottom-width: 3px;  /* 增加底部边框厚度，更明显 */
    }
    
    QTabBar::tab:hover:!selected {
        background-color: rgba(255, 255, 255, 0.05);
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }
    
    /* 添加标签溢出时的滚动按钮样式 */
    QTabBar::scroller {
        width: 20px;
    }
    
    QTabBar QToolButton {
        background-color: """ + background_color + """;
        border: none;
        color: """ + text_secondary + """;
        border-radius: 2px;
        margin: 1px;
    }
    
    QTabBar QToolButton:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    /* 为左右箭头添加Unicode字符 */
    QTabBar QToolButton::right-arrow {
        image: none;
        background: transparent;
        qproperty-text: "\u25B6"; /* Unicode右三角形 ▶ */
        qproperty-autoRaise: true;
        width: 16px;
        height: 16px;
    }
    
    QTabBar QToolButton::left-arrow {
        image: none;
        background: transparent;
        qproperty-text: "\u25C0"; /* Unicode左三角形 ◀ */
        qproperty-autoRaise: true;
        width: 16px;
        height: 16px;
    }
    
    /* ======== 按钮样式 ======== */
    QPushButton {
        background-color: """ + primary_color + """;
        color: white;
        border: none;
        border-radius: 3px;
        padding: 4px 8px;
        font-weight: bold;
        min-width: 60px;
        min-height: 24px;
        font-size: 13px;
    }
    
    QPushButton:hover {
        background-color: """ + primary_dark_color + """;
    }
    
    QPushButton:pressed {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 """ + primary_dark_color + """, 
                                      stop: 1 """ + primary_color + """);
    }
    
    QPushButton:disabled {
        background-color: #555555;
        color: #888888;
    }
    
    /* ======== 标签样式 ======== */
    QLabel {
        color: """ + text_primary + """;
        background-color: transparent;
        font-size: 13px;
    }
    
    /* ======== 分组框样式 ======== */
    QGroupBox {
        font-weight: bold;
        border: 1px solid """ + divider_color + """;
        border-radius: 3px;
        margin-top: 14px;
        padding-top: 14px;
        padding-bottom: 6px;
        background-color: """ + card_background + """;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 4px;
        color: """ + primary_light_color + """;
        background-color: transparent;
        font-size: 13px;
    }
    
    /* ======== 滚动区域样式 ======== */
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    
    /* ======== 滚动条样式 ======== */
    QScrollBar:vertical {
        border: none;
        background-color: """ + surface_color + """;
        width: 5px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #4A4A4A;
        min-height: 25px;
        border-radius: 2px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #5A5A5A;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background-color: """ + surface_color + """;
        height: 5px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #4A4A4A;
        min-width: 25px;
        border-radius: 2px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #5A5A5A;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    /* ======== 表格样式 ======== */
    QTableWidget {
        gridline-color: """ + divider_color + """;
        border: 1px solid """ + divider_color + """;
        border-radius: 0px;
        background-color: """ + card_background + """;
        selection-background-color: rgba(92, 107, 192, 0.3);
        selection-color: """ + text_primary + """;
    }
    
    QTableWidget::item {
        padding: 3px;
        background-color: transparent;
        font-size: 11px;
    }
    
    QTableWidget::item:selected {
        background-color: rgba(92, 107, 192, 0.3);
        color: """ + text_primary + """;
    }
    
    QTableWidget::item:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    QHeaderView::section {
        background-color: """ + surface_color + """;
        padding: 3px;
        border: none;
        border-right: 1px solid """ + divider_color + """;
        border-bottom: 1px solid """ + divider_color + """;
        font-weight: bold;
        color: """ + text_secondary + """;
        font-size: 11px;
    }
    
    /* ======== 输入框样式 ======== */
    QLineEdit, QTextEdit, QPlainTextEdit {
        border: 1px solid """ + divider_color + """;
        border-radius: 3px;
        padding: 3px 6px;
        background-color: """ + surface_color + """;
        selection-background-color: """ + primary_color + """;
        selection-color: white;
        color: """ + text_primary + """;
        min-height: 22px;
        font-size: 13px;
    }
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid """ + primary_color + """;
    }
    
    QLineEdit:disabled {
        background-color: #383838;
        color: #7A7A7A;
    }
    
    /* ======== 下拉框样式 ======== */
    QComboBox {
        border: 1px solid """ + divider_color + """;
        border-radius: 2px;
        padding: 2px 6px;
        background-color: """ + surface_color + """;
        selection-background-color: """ + primary_color + """;
        selection-color: white;
        color: """ + text_primary + """;
        min-height: 16px;
        font-size: 11px;
    }
    
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 14px;
        border-left: none;
    }
    
    QComboBox::down-arrow {
        width: 10px;
        height: 10px;
        background-color: """ + text_secondary + """;
        border-radius: 2px;
    }
    
    QComboBox QAbstractItemView {
        border: 1px solid """ + divider_color + """;
        border-radius: 0px;
        background-color: """ + surface_color + """;
        selection-background-color: """ + primary_color + """;
        selection-color: white;
        font-size: 11px;
    }
    
    /* ======== 复选框样式 ======== */
    QCheckBox {
        spacing: 4px;
        color: """ + text_primary + """;
        background-color: transparent;
        padding: 0px;
        min-height: 14px;
        font-size: 11px;
    }
    
    QCheckBox::indicator {
        width: 12px;
        height: 12px;
        background-color: """ + surface_color + """;
        border: 1px solid """ + text_secondary + """;
        border-radius: 2px;
    }
    
    QCheckBox::indicator:checked {
        background-color: """ + primary_color + """;
        border: 1px solid """ + primary_color + """;
    }
    
    QCheckBox::indicator:hover {
        border: 1px solid """ + primary_light_color + """;
    }
    
    /* ======== 单选按钮样式 ======== */
    QRadioButton {
        spacing: 4px;
        color: """ + text_primary + """;
        background-color: transparent;
        min-height: 14px;
        font-size: 11px;
    }
    
    QRadioButton::indicator {
        width: 12px;
        height: 12px;
        border-radius: 6px;
        background-color: """ + surface_color + """;
        border: 1px solid """ + text_secondary + """;
    }
    
    QRadioButton::indicator:checked {
        background-color: """ + primary_color + """;
        border: 2px solid """ + surface_color + """;
    }
    
    QRadioButton::indicator:hover {
        border: 1px solid """ + primary_light_color + """;
    }
    
    /* ======== 进度条样式 ======== */
    QProgressBar {
        border: none;
        border-radius: 2px;
        background-color: """ + surface_color + """;
        height: 5px;
        text-align: center;
        color: transparent;
    }
    
    QProgressBar::chunk {
        background-color: """ + accent_color + """;
        border-radius: 2px;
    }
    
    /* ======== 状态栏样式 ======== */
    QStatusBar {
        background-color: """ + surface_color + """;
        color: """ + text_secondary + """;
        border-top: 1px solid """ + divider_color + """;
        font-size: 11px;
    }
    
    /* ======== 工具提示样式 ======== */
    QToolTip {
        border: 1px solid """ + divider_color + """;
        border-radius: 2px;
        background-color: """ + surface_color + """;
        color: """ + text_primary + """;
        padding: 3px;
        font-size: 11px;
    }
    
    /* ======== 卡片样式 ======== */
    #materialCard {
        background-color: """ + card_background + """;
        border-radius: 2px;
        border: 1px solid """ + divider_color + """;
    }
    
    /* ======== 框架样式 ======== */
    QFrame {
        border: none;
        background-color: transparent;
    }
    
    QFrame[frameShape="4"], QFrame[frameShape="5"], QFrame[frameShape="6"] {
        background-color: """ + divider_color + """;
    }
    
    QFrame#separator {
        background-color: """ + divider_color + """;
        max-height: 1px;
        border: none;
    }
    
    /* ======== 特定页面样式 ======== */
    QWidget#home_tab, QWidget#epub_splitter_tab, QWidget#condenser_tab, QWidget#txt_to_epub_tab, QWidget#api_test_tab {
        background-color: """ + background_color + """;
    }
    
    /* ======== 脱水处理页面专用样式 ======== */
    /* 保持优化布局，但使用合适的字体 */
    QWidget#condenser_tab {
        margin: 0;
        padding: 0;
    }
    
    /* 脱水页面组件样式 */
    QWidget#condenser_tab QGroupBox {
        margin-top: 10px;
        margin-bottom: 5px;
        padding: 2px;
        padding-top: 16px; /* 为标题留出空间 */
        font-size: 12px;
    }

    QWidget#condenser_tab QGroupBox::title {
        padding: 0 3px;
        font-size: 12px;
        subcontrol-position: top left;
    }
    
    /* 脱水页面标签 */
    QWidget#condenser_tab QLabel {
        padding: 0px;
        margin: 0px;
        font-size: 12px;
        max-height: 16px;
    }
    
    /* 脱水页面章节范围标签 */
    QWidget#condenser_tab QLabel#start_chapter_label, 
    QWidget#condenser_tab QLabel#end_chapter_label {
        font-size: 12px;
    }
    
    /* 脱水比例区间标签 */
    QWidget#condenser_tab QLabel#ratio_range_label {
        font-size: 12px;
    }
    
    /* 脱水页面输入框 */
    QWidget#condenser_tab QLineEdit {
        padding: 2px 4px;
        height: 22px;
        min-height: 22px;
        font-size: 12px;
        background-color: """ + surface_color + """;  /* 使用暗色背景 */
        border: 1px solid """ + divider_color + """;
        color: """ + text_primary + """;
    }
    
    QWidget#condenser_tab QLineEdit:focus {
        border: 1px solid """ + primary_color + """;
    }
    
    /* 脱水页面浏览按钮 */
    QWidget#condenser_tab QPushButton#browse_button,
    QWidget#condenser_tab QPushButton#output_browse_button {
        padding: 2px 5px;
        min-width: 40px;
        min-height: 22px;
        max-height: 22px;
        font-size: 12px;
    }
    
    /* 脱水页面SpinBox */
    QWidget#condenser_tab QSpinBox, 
    QWidget#condenser_tab QDoubleSpinBox {
        padding: 1px 2px;
        height: 22px;
        min-height: 22px;
        max-height: 22px;
        font-size: 12px;
        background-color: """ + surface_color + """;  /* 使用暗色背景 */
        border: 1px solid """ + divider_color + """;
        color: """ + text_primary + """;
    }
    
    QWidget#condenser_tab QSpinBox:focus, 
    QWidget#condenser_tab QDoubleSpinBox:focus {
        border: 1px solid """ + primary_color + """;
    }
    
    QWidget#condenser_tab QSpinBox::up-button, 
    QWidget#condenser_tab QDoubleSpinBox::up-button,
    QWidget#condenser_tab QSpinBox::down-button, 
    QWidget#condenser_tab QDoubleSpinBox::down-button {
        background-color: """ + surface_color + """;
        border-left: 1px solid """ + divider_color + """;
        width: 14px;
    }
    
    /* 脱水页面复选框 */
    QWidget#condenser_tab QCheckBox {
        spacing: 4px;
        font-size: 12px;
        min-height: 16px;
        max-height: 16px;
    }
    
    QWidget#condenser_tab QCheckBox::indicator {
        width: 14px;
        height: 14px;
    }
    
    /* 脱水页面进度条 */
    QWidget#condenser_tab QProgressBar {
        max-height: 6px;
        min-height: 6px;
        font-size: 0px; /* 隐藏文字 */
    }
    
    /* 脱水页面状态标签 */
    QWidget#condenser_tab QLabel#status_label {
        font-weight: bold;
        min-height: 16px;
        max-height: 16px;
        font-size: 12px;
    }
    
    /* 优化布局间距 */
    QWidget#condenser_tab QHBoxLayout, 
    QWidget#condenser_tab QVBoxLayout {
        margin: 1px;
        padding: 1px;
        spacing: 2px;
    }
    
    /* 脱水页面日志区文本 */
    QWidget#condenser_tab QTextEdit {
        font-size: 12px;
        padding: 3px;
        background-color: """ + surface_color + """;  /* 使用暗色背景 */
        border: 1px solid """ + divider_color + """;
        color: """ + text_primary + """;
    }
    
    QWidget#condenser_tab QTextEdit:focus {
        border: 1px solid """ + primary_color + """;
    }
    
    /* 脱水页面开始脱水按钮 */
    QWidget#condenser_tab QPushButton#start_button {
        background-color: """ + accent_color + """;
        padding: 4px 8px;
        min-height: 24px;
        font-size: 13px;
        font-weight: bold;
    }
    
    QWidget#condenser_tab QPushButton#start_button:hover {
        background-color: """ + accent_dark_color + """;
    }
    
    /* 脱水页面清除日志按钮 */
    QWidget#condenser_tab QPushButton#clear_log_button {
        min-width: 70px;
        padding: 2px 5px;
        font-size: 12px;
    }
    
    /* 脱水页面自动换行复选框 */
    QWidget#condenser_tab QCheckBox#wrap_checkbox {
        font-size: 12px;
    }
    
    /* ======== SpinBox样式 ======== */
    QSpinBox, QDoubleSpinBox {
        border: 1px solid """ + divider_color + """;
        border-radius: 3px;
        padding: 2px 4px;
        background-color: """ + surface_color + """;
        selection-background-color: """ + primary_color + """;
        selection-color: white;
        color: """ + text_primary + """;
        min-height: 22px;
        font-size: 13px;
    }
    
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        background-color: """ + surface_color + """;
        border-left: 1px solid """ + divider_color + """;
        border-bottom: 1px solid """ + divider_color + """;
        border-top-right-radius: 3px;
        width: 18px;
        height: 10px;
    }
    
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        background-color: """ + surface_color + """;
        border-left: 1px solid """ + divider_color + """;
        border-bottom-right-radius: 3px;
        width: 18px;
        height: 10px;
    }
    
    /* 简化箭头定义 */
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 0 4px 4px 4px;
        border-color: transparent transparent white transparent;
    }
    
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 4px 4px 0 4px;
        border-color: white transparent transparent transparent;
    }
    
    /* 脱水页面上下按钮 */
    QWidget#condenser_tab QSpinBox::up-button, 
    QWidget#condenser_tab QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        background-color: """ + surface_color + """;
        border-left: 1px solid """ + divider_color + """;
        border-bottom: 1px solid """ + divider_color + """;
        width: 18px;
        height: 10px;
    }
    
    QWidget#condenser_tab QSpinBox::down-button, 
    QWidget#condenser_tab QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        background-color: """ + surface_color + """;
        border-left: 1px solid """ + divider_color + """;
        width: 18px;
        height: 10px;
    }
    
    /* 脱水页面箭头 */
    QWidget#condenser_tab QSpinBox::up-arrow, 
    QWidget#condenser_tab QDoubleSpinBox::up-arrow {
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 0 4px 4px 4px;
        border-color: transparent transparent white transparent;
    }
    
    QWidget#condenser_tab QSpinBox::down-arrow, 
    QWidget#condenser_tab QDoubleSpinBox::down-arrow {
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 4px 4px 0 4px;
        border-color: white transparent transparent transparent;
    }
    
    /* 增加按钮悬停效果 */
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover,
    QWidget#condenser_tab QSpinBox::up-button:hover, 
    QWidget#condenser_tab QDoubleSpinBox::up-button:hover,
    QWidget#condenser_tab QSpinBox::down-button:hover, 
    QWidget#condenser_tab QDoubleSpinBox::down-button:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid """ + primary_color + """;
    }
    
    QSpinBox:disabled, QDoubleSpinBox:disabled {
        background-color: #383838;
        color: #7A7A7A;
    }
    
    /* ======== API测试页面专用样式 ======== */
    QWidget#api_test_tab {
        background-color: """ + background_color + """;
    }
    
    QWidget#api_test_tab QWidget {
        background-color: """ + background_color + """;
    }
    
    QWidget#api_test_tab QLabel {
        background-color: transparent;
    }
    
    QWidget#api_test_tab QPushButton#test_all_button {
        background-color: """ + accent_color + """;
        margin-bottom: 5px;
    }
    
    QWidget#api_test_tab QPushButton#test_all_button:hover {
        background-color: """ + accent_dark_color + """;
    }
    
    QWidget#api_test_tab QPushButton#reload_button {
        background-color: """ + primary_color + """;
        margin-bottom: 5px;
    }
    
    QWidget#api_test_tab QPushButton#reload_button:hover {
        background-color: """ + primary_dark_color + """;
    }
    
    QWidget#api_test_tab QTableWidget {
        background-color: """ + card_background + """;
        border: 1px solid """ + divider_color + """;
    }
    
    QWidget#api_test_tab QVBoxLayout,
    QWidget#api_test_tab QHBoxLayout {
        background-color: """ + background_color + """;
        margin: 0;
        padding: 0;
    }
    """

# 定义特定控件或特殊场景的额外样式
def get_accent_button_style():
    """返回强调色按钮的样式"""
    return """
    QPushButton {
        background-color: #7986CB;
        color: white;
        border: none;
        border-radius: 2px;
        padding: 3px 6px;
        font-weight: bold;
        min-width: 60px;
        min-height: 18px;
        font-size: 11px;
    }
    
    QPushButton:hover {
        background-color: #5C6BC0;
    }
    
    QPushButton:pressed {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #5C6BC0, 
                                      stop: 1 #7986CB);
    }
    """

def get_flat_button_style():
    """返回扁平按钮的样式"""
    return """
    QPushButton {
        background-color: transparent;
        color: #7986CB;
        border: none;
        font-weight: bold;
        font-size: 11px;
    }
    
    QPushButton:hover {
        background-color: rgba(121, 134, 203, 0.1);
    }
    
    QPushButton:pressed {
        background-color: rgba(121, 134, 203, 0.2);
    }
    """ 