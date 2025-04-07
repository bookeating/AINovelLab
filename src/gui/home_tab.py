#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的首页标签页
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class HomeTab(QWidget):
    """首页标签页，介绍应用程序的使用方法"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建布局
        main_layout = QVBoxLayout()
        
        # 创建滚动区域，以便显示大量文本
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # 添加标题
        title_label = QLabel("AI小说实验室使用指南")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)
        
        # 添加应用简介
        intro_group = QGroupBox("应用简介")
        intro_layout = QVBoxLayout()
        intro_text = QLabel("""本应用是一个AI驱动的小说处理实验室，主要用于将EPUB电子书进行"脱水"处理（压缩内容），
使其内容更加精简。整个处理流程分为三个步骤：

1. EPUB转TXT：将EPUB电子书转换为TXT文件
2. 脱水处理：对TXT文件进行内容压缩
3. TXT转EPUB：将处理后的TXT文件重新转换为EPUB格式

由于脱水处理可能需要较长时间，本工具支持选择性地处理部分章节。""")
        intro_text.setWordWrap(True)
        intro_layout.addWidget(intro_text)
        intro_group.setLayout(intro_layout)
        content_layout.addWidget(intro_group)
        
        # 添加使用流程
        flow_group = QGroupBox("使用流程")
        flow_layout = QVBoxLayout()
        
        step1_title = QLabel("步骤一：EPUB转TXT")
        step1_title.setFont(QFont("", 10, QFont.Bold))
        step1_text = QLabel("""1. 点击"EPUB转TXT"标签页
2. 点击"浏览..."按钮选择需要处理的EPUB文件
3. 选择或确认输出目录（默认为EPUB文件所在目录）
4. 设置每个文件的章节数（默认为1，即每个章节单独保存为一个TXT文件）
5. 点击"开始分割"按钮开始处理
6. 等待处理完成""")
        step1_text.setWordWrap(True)
        
        step2_title = QLabel("步骤二：脱水处理")
        step2_title.setFont(QFont("", 10, QFont.Bold))
        step2_text = QLabel("""1. 点击"脱水处理"标签页
2. 点击"浏览..."按钮选择包含TXT文件的文件夹（通常是步骤一的输出目录）
3. 设置需要处理的章节范围（可以只处理部分章节，特别是对于长篇小说）
4. 点击"开始脱水"按钮开始处理
5. 等待处理完成（这一步可能需要较长时间，取决于章节数量和内容长度）

注意：脱水处理需要使用Gemini API，请确保api_keys.json文件中已配置有效的API密钥""")
        step2_text.setWordWrap(True)
        
        step3_title = QLabel("步骤三：TXT转EPUB")
        step3_title.setFont(QFont("", 10, QFont.Bold))
        step3_text = QLabel("""1. 点击"TXT转EPUB"标签页
2. 点击"浏览..."按钮选择包含处理后TXT文件的文件夹
3. 选择或确认EPUB输出路径
4. 设置或确认小说标题和作者信息
5. 点击"开始合并"按钮开始处理
6. 等待处理完成""")
        step3_text.setWordWrap(True)
        
        flow_layout.addWidget(step1_title)
        flow_layout.addWidget(step1_text)
        flow_layout.addSpacing(10)
        flow_layout.addWidget(step2_title)
        flow_layout.addWidget(step2_text)
        flow_layout.addSpacing(10)
        flow_layout.addWidget(step3_title)
        flow_layout.addWidget(step3_text)
        flow_group.setLayout(flow_layout)
        content_layout.addWidget(flow_group)
        
        # 添加注意事项
        notes_group = QGroupBox("注意事项")
        notes_layout = QVBoxLayout()
        notes_text = QLabel("""1. API密钥配置：脱水处理需要使用Gemini API，请在api_keys.json文件中配置有效的API密钥
2. 处理时间：脱水处理可能需要较长时间，特别是对于内容较多的小说
3. 章节范围：对于长篇小说，建议分批处理，每次选择一定范围的章节进行脱水
4. 文件命名：本工具依赖于特定的文件命名格式来识别章节顺序，请勿手动修改生成的文件名
5. 数据备份：处理前建议备份原始EPUB文件，以防止意外情况导致数据丢失""")
        notes_text.setWordWrap(True)
        notes_layout.addWidget(notes_text)
        notes_group.setLayout(notes_layout)
        content_layout.addWidget(notes_group)
        
        # 设置滚动区域的内容
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout) 