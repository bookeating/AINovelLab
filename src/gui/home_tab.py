#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的首页标签页
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox, QScrollArea,
                            QHBoxLayout, QGridLayout, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from .resources import get_icon

class CardWidget(QFrame):
    """Material Design 风格的卡片控件"""
    
    def __init__(self, title, icon_name, description, parent=None):
        super().__init__(parent)
        self.setObjectName("materialCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 创建卡片布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 创建标题和图标的水平布局
        header_layout = QHBoxLayout()
        
        # 添加图标
        icon_label = QLabel()
        icon_label.setStyleSheet("background-color: transparent;")
        icon = get_icon(icon_name)
        if not icon.isNull():
            pixmap = icon.pixmap(32, 32)
            icon_label.setPixmap(pixmap)
        header_layout.addWidget(icon_label)
        
        # 添加标题
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #7986CB; background-color: transparent;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 添加标题布局到卡片
        layout.addLayout(header_layout)
        
        # 添加描述文本
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #E0E0E0; background-color: transparent;")
        layout.addWidget(desc_label)

class HomeTab(QWidget):
    """首页标签页，介绍应用程序的使用方法"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("home_tab")
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 创建滚动区域，以便显示大量文本
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        
        # 创建内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(24)
        
        # 添加标题
        title_label = QLabel("AI小说实验室使用指南")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #A5B3E0; margin-bottom: 16px; background-color: transparent;")
        content_layout.addWidget(title_label)
        
        # 添加应用简介卡片
        intro_card = CardWidget(
            "应用简介", 
            "book",
            """本应用是一个AI驱动的小说处理实验室，主要用于将EPUB电子书进行"脱水"处理（压缩内容），
使其内容更加精简。整个处理流程分为三个步骤：

1. EPUB转TXT：将EPUB电子书转换为TXT文件
2. 脱水处理：对TXT文件进行内容压缩
3. TXT转EPUB：将处理后的TXT文件重新转换为EPUB格式

由于脱水处理可能需要较长时间，本工具支持选择性地处理部分章节。"""
        )
        content_layout.addWidget(intro_card)
        
        # 添加使用流程区域标题
        flow_title = QLabel("使用流程")
        flow_title.setFont(QFont("", 14, QFont.Bold))
        flow_title.setStyleSheet("color: #A5B3E0; margin-top: 8px; background-color: transparent;")
        content_layout.addWidget(flow_title)
        
        # 使用网格布局来放置三个卡片
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(16)
        cards_layout.setVerticalSpacing(16)
        
        # 添加步骤一卡片
        step1_card = CardWidget(
            "步骤一：EPUB转TXT", 
            "book",
            """1. 点击"EPUB转TXT"标签页
2. 点击"浏览..."按钮选择需要处理的EPUB文件
3. 选择或确认输出目录（默认为EPUB文件所在目录）
4. 设置每个文件的章节数（默认为1，即每个章节单独保存为一个TXT文件）
5. 点击"开始分割"按钮开始处理
6. 等待处理完成"""
        )
        cards_layout.addWidget(step1_card, 0, 0)
        
        # 添加步骤二卡片
        step2_card = CardWidget(
            "步骤二：脱水处理", 
            "water",
            """1. 点击"脱水处理"标签页
2. 点击"浏览..."按钮选择包含TXT文件的文件夹（通常是步骤一的输出目录）
3. 设置需要处理的章节范围（可以只处理部分章节，特别是对于长篇小说）
4. 点击"开始脱水"按钮开始处理
5. 等待处理完成（这一步可能需要较长时间，取决于章节数量和内容长度）

注意：脱水处理需要使用Gemini API，请确保api_keys.json文件中已配置有效的API密钥"""
        )
        cards_layout.addWidget(step2_card, 0, 1)
        
        # 添加步骤三卡片
        step3_card = CardWidget(
            "步骤三：TXT转EPUB", 
            "convert",
            """1. 点击"TXT转EPUB"标签页
2. 点击"浏览..."按钮选择包含处理后TXT文件的文件夹
3. 选择或确认EPUB输出路径
4. 设置或确认小说标题和作者信息
5. 点击"开始合并"按钮开始处理
6. 等待处理完成"""
        )
        cards_layout.addWidget(step3_card, 1, 0)
        
        # 添加注意事项卡片
        notes_card = CardWidget(
            "注意事项", 
            "settings",
            """1. API密钥配置：脱水处理需要使用Gemini API，请在api_keys.json文件中配置有效的API密钥
2. 处理时间：脱水处理可能需要较长时间，特别是对于内容较多的小说
3. 章节范围：对于长篇小说，建议分批处理，每次选择一定范围的章节进行脱水
4. 文件命名：本工具依赖于特定的文件命名格式来识别章节顺序，请勿手动修改生成的文件名
5. 数据备份：处理前建议备份原始EPUB文件，以防止意外情况导致数据丢失"""
        )
        cards_layout.addWidget(notes_card, 1, 1)
        
        # 将卡片网格添加到内容布局
        content_layout.addLayout(cards_layout)
        
        # 添加底部留白
        content_layout.addStretch()
        
        # 设置滚动区域的内容
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout) 