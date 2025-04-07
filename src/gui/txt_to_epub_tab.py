#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的TXT转EPUB标签页
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                          QFileDialog, QMessageBox, QProgressBar, QTextEdit, 
                          QGroupBox, QLineEdit, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor

from .worker import WorkerThread

class TxtToEpubTab(QWidget):
    """TXT转EPUB标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.worker_thread = None
        self.txt_files = []
        self.book_base_dir = ""  # 保存书名目录路径
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建布局
        main_layout = QVBoxLayout()
        
        # 创建左右分栏布局
        split_layout = QHBoxLayout()
        
        # 左侧面板 - 控制区域
        left_panel = QVBoxLayout()
        
        # 文件夹选择
        folder_group = QGroupBox("选择TXT文件夹")
        folder_layout = QHBoxLayout()
        
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        self.folder_path_edit.setPlaceholderText("请选择TXT文件所在文件夹...")
        
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(browse_button)
        folder_group.setLayout(folder_layout)
        
        # EPUB设置
        epub_group = QGroupBox("EPUB设置")
        epub_layout = QFormLayout()
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入书籍标题...")
        
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("输入作者名...")
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText("EPUB输出位置...")
        
        output_browse_button = QPushButton("浏览...")
        output_browse_button.clicked.connect(self.browse_output)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(output_browse_button)
        
        epub_layout.addRow("书籍标题:", self.title_edit)
        epub_layout.addRow("作者:", self.author_edit)
        epub_layout.addRow("输出文件:", output_layout)
        
        epub_group.setLayout(epub_layout)
        
        # 状态和进度
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("就绪")
        
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        
        # 文件列表显示
        files_group = QGroupBox("文件列表")
        files_layout = QVBoxLayout()
        
        self.files_text = QTextEdit()
        self.files_text.setReadOnly(True)
        
        files_layout.addWidget(self.files_text)
        files_group.setLayout(files_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("生成EPUB")
        self.start_button.clicked.connect(self.start_merging)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        
        # 将控制组件添加到左侧面板
        left_panel.addWidget(folder_group)
        left_panel.addWidget(epub_group)
        left_panel.addWidget(status_group)
        left_panel.addWidget(files_group)
        left_panel.addLayout(button_layout)
        
        # 右侧面板 - 日志区域
        right_panel = QVBoxLayout()
        
        # 日志显示区域
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)  # 禁用自动换行
        
        # 在底部添加清除日志按钮和自动滚动选项
        log_buttons_layout = QHBoxLayout()
        self.auto_scroll_checkbox = QCheckBox("自动滚动")
        self.auto_scroll_checkbox.setToolTip("勾选后日志会自动滚动到底部，取消勾选则保持当前位置")
        self.auto_scroll_checkbox.setChecked(False)  # 默认不自动滚动
        
        self.line_wrap_checkbox = QCheckBox("自动换行")
        self.line_wrap_checkbox.setToolTip("勾选后文本会自动换行显示，取消勾选则需要水平滚动查看")
        self.line_wrap_checkbox.setChecked(False)  # 默认不自动换行
        self.line_wrap_checkbox.stateChanged.connect(self.toggle_line_wrap)
        
        self.clear_log_button = QPushButton("清除日志")
        self.clear_log_button.clicked.connect(self.clear_log)
        
        log_buttons_layout.addWidget(self.auto_scroll_checkbox)
        log_buttons_layout.addWidget(self.line_wrap_checkbox)
        log_buttons_layout.addStretch()
        log_buttons_layout.addWidget(self.clear_log_button)
        
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_buttons_layout)
        log_group.setLayout(log_layout)
        
        # 将日志组件添加到右侧面板
        right_panel.addWidget(log_group)
        
        # 将左右面板添加到分栏布局
        split_layout.addLayout(left_panel, 1)  # 比例1
        split_layout.addLayout(right_panel, 1)  # 比例1
        
        # 将分栏布局添加到主布局
        main_layout.addLayout(split_layout)
        
        self.setLayout(main_layout)
    
    def add_log(self, message):
        """添加日志到日志显示区域"""
        self.log_text.append(message.rstrip())
        
        # 只在启用自动滚动时，才滚动到底部
        if self.auto_scroll_checkbox.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """清除日志显示区域的内容"""
        self.log_text.clear()
    
    def on_condense_path_changed(self, base_dir, condense_dir):
        """处理脱水完成的信号"""
        self.book_base_dir = base_dir
        
        # 设置输入目录为脱水结果目录
        self.folder_path_edit.setText(condense_dir)
        self.load_txt_files(condense_dir)
        
        # 尝试设置EPUB输出文件
        book_name = os.path.basename(self.book_base_dir)
        if book_name:
            # 设置书名
            self.title_edit.setText(book_name)
            
            # 设置EPUB输出路径在书名目录下
            output_epub_path = os.path.join(self.book_base_dir, f"{book_name}.epub")
            self.output_path_edit.setText(output_epub_path)
            self.add_log(f"设置EPUB输出路径: {output_epub_path}")
    
    def browse_folder(self):
        """浏览并选择TXT文件所在文件夹"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择TXT文件所在文件夹", ""
        )
        if dir_path:
            self.folder_path_edit.setText(dir_path)
            self.load_txt_files(dir_path)
            
            # 尝试推断书名目录
            parent_dir = os.path.dirname(dir_path)
            folder_name = os.path.basename(dir_path)
            
            if folder_name.lower() == "condensed":
                # 如果选择的是condensed目录，则其父目录可能是书名目录
                self.book_base_dir = parent_dir
                book_name = os.path.basename(parent_dir)
                
                # 设置书名
                self.title_edit.setText(book_name)
                
                # 设置EPUB输出路径在书名目录下
                output_epub_path = os.path.join(parent_dir, f"{book_name}.epub")
                self.output_path_edit.setText(output_epub_path)
                self.add_log(f"设置EPUB输出路径: {output_epub_path}")
    
    def browse_output(self):
        """浏览并选择EPUB输出位置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择EPUB输出位置", "", "EPUB Files (*.epub);;All Files (*)"
        )
        if file_path:
            # 确保文件有.epub扩展名
            if not file_path.lower().endswith('.epub'):
                file_path += '.epub'
            self.output_path_edit.setText(file_path)
            
            # 添加日志
            self.add_log(f"已设置EPUB输出路径: {file_path}")
    
    def load_txt_files(self, folder_path):
        """加载文件夹中的TXT文件"""
        self.txt_files = []
        files_text = ""
        
        # 查找所有TXT文件
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.txt'):
                file_path = os.path.join(folder_path, file_name)
                self.txt_files.append(file_path)
                files_text += f"{file_name}\n"
        
        # 更新文件列表显示
        self.files_text.setText(files_text)
        
        # 添加日志
        self.add_log(f"已加载{len(self.txt_files)}个TXT文件")
    
    def start_merging(self):
        """开始合并操作"""
        # 检查输入参数
        folder_path = self.folder_path_edit.text()
        output_path = self.output_path_edit.text()
        title = self.title_edit.text()
        author = self.author_edit.text()
        
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "错误", "请选择有效的TXT文件夹")
            return
        
        if not output_path:
            QMessageBox.warning(self, "错误", "请选择EPUB输出位置")
            return
        
        if not title:
            title = "未命名"
        
        if not author:
            author = "未知作者"
        
        if not self.txt_files:
            QMessageBox.warning(self, "错误", "所选文件夹中未找到TXT文件")
            return
        
        # 准备参数
        args = {
            'txt_files': self.txt_files,
            'output_path': output_path,
            'title': title,
            'author': author
        }
        
        # 创建并启动工作线程
        self.worker_thread = WorkerThread('merge', args)
        self.worker_thread.update_progress.connect(self.update_progress)
        self.worker_thread.operation_complete.connect(self.operation_complete)
        self.worker_thread.log_message.connect(self.add_log)
        
        # 更新UI状态
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在生成EPUB...")
        
        # 添加开始日志
        self.add_log(f"开始生成EPUB，标题: {title}，作者: {author}")
        self.add_log(f"输出路径: {output_path}")
        self.add_log(f"共{len(self.txt_files)}个章节")
        
        # 启动线程
        self.worker_thread.start()
    
    def update_progress(self, value, message):
        """更新进度条和状态标签"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def operation_complete(self, success, message):
        """操作完成的处理函数"""
        self.start_button.setEnabled(True)
        
        if success:
            self.status_label.setText("EPUB生成完成")
            self.add_log("EPUB生成成功完成")
            QMessageBox.information(self, "操作完成", message)
        else:
            self.status_label.setText("EPUB生成失败")
            self.add_log(f"EPUB生成失败: {message}")
            QMessageBox.critical(self, "操作失败", message)
            
    def toggle_line_wrap(self, state):
        """切换自动换行选项"""
        if state == Qt.Checked:
            self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.log_text.setLineWrapMode(QTextEdit.NoWrap) 