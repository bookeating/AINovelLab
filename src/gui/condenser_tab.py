#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的脱水处理标签页
"""

import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QFileDialog, QMessageBox, QProgressBar, QTextEdit, 
                           QSpinBox, QGroupBox, QLineEdit, QCheckBox)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QTextCursor

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 从核心模块导入处理脚本
try:
    from core.novel_condenser import config, key_manager
    import core.novel_condenser.main as main_module  # 直接导入整个main模块
except ImportError:
    from src.core.novel_condenser import config, key_manager
    import src.core.novel_condenser.main as main_module  # 直接导入整个main模块

from .worker import WorkerThread

class CondenserTab(QWidget):
    """小说脱水标签页"""
    
    # 定义信号，脱水完成后发送书名目录和脱水结果目录
    condense_complete = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.worker_thread = None
        self.txt_files = []
        self.book_base_dir = ""  # 保存书名目录路径
        self.output_dir = ""  # 保存脱水输出目录
        
        # 初始化时加载API配置
        try:
            config.load_api_config()
        except Exception as e:
            self.add_log(f"加载API配置时出错: {str(e)}")
    
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
        
        # 输出目录选择
        output_group = QGroupBox("脱水输出目录")
        output_layout = QHBoxLayout()
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.setPlaceholderText("脱水处理结果输出目录...")
        
        output_browse_button = QPushButton("浏览...")
        output_browse_button.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(output_browse_button)
        output_group.setLayout(output_layout)
        
        # 章节范围选择
        range_group = QGroupBox("脱水章节范围")
        range_layout = QHBoxLayout()
        
        self.start_chapter_label = QLabel("开始章节:")
        self.start_chapter_spin = QSpinBox()
        self.start_chapter_spin.setRange(1, 10000)
        self.start_chapter_spin.setValue(1)
        
        self.end_chapter_label = QLabel("结束章节:")
        self.end_chapter_spin = QSpinBox()
        self.end_chapter_spin.setRange(1, 10000)
        self.end_chapter_spin.setValue(9999)
        
        range_layout.addWidget(self.start_chapter_label)
        range_layout.addWidget(self.start_chapter_spin)
        range_layout.addWidget(self.end_chapter_label)
        range_layout.addWidget(self.end_chapter_spin)
        range_layout.addStretch()
        range_group.setLayout(range_layout)
        
        # 添加强制生成选项
        options_group = QGroupBox("脱水选项")
        options_layout = QVBoxLayout()
        
        self.force_regenerate_checkbox = QCheckBox("强制生成")
        self.force_regenerate_checkbox.setToolTip("勾选后将强制重新脱水，否则跳过已存在的文件")
        
        options_layout.addWidget(self.force_regenerate_checkbox)
        options_group.setLayout(options_layout)
        
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
        self.start_button = QPushButton("开始脱水")
        self.start_button.clicked.connect(self.start_condensing)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        
        # 将控制组件添加到左侧面板
        left_panel.addWidget(folder_group)
        left_panel.addWidget(output_group)
        left_panel.addWidget(range_group)
        left_panel.addWidget(options_group)
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
    
    def on_split_path_changed(self, base_dir, split_dir):
        """处理EPUB分割完成的信号"""
        self.book_base_dir = base_dir
        
        # 设置输入目录为分割结果目录
        self.folder_path_edit.setText(split_dir)
        self.load_txt_files(split_dir)
        
        # 设置脱水输出目录为"书名目录/condensed"
        self.output_dir = os.path.join(self.book_base_dir, "condensed")
        
        # 如果目录不存在，创建目录
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except Exception as e:
                QMessageBox.warning(self, "警告", f"无法创建脱水输出目录: {str(e)}")
                # 如果创建失败，使用分割结果目录作为默认输出目录
                self.output_dir = split_dir
        
        self.output_dir_edit.setText(self.output_dir)
        self.add_log(f"设置脱水输出目录: {self.output_dir}")
    
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
            
            if folder_name.lower() == "splitted":
                # 如果选择的是splitted目录，则其父目录可能是书名目录
                self.book_base_dir = parent_dir
                # 设置脱水输出目录为兄弟目录"condensed"
                self.output_dir = os.path.join(self.book_base_dir, "condensed")
                
                # 如果目录不存在，创建目录
                if not os.path.exists(self.output_dir):
                    try:
                        os.makedirs(self.output_dir)
                    except Exception as e:
                        QMessageBox.warning(self, "警告", f"无法创建脱水输出目录: {str(e)}")
                        # 如果创建失败，使用选择的目录作为输出目录
                        self.output_dir = dir_path
                
                self.output_dir_edit.setText(self.output_dir)
                self.add_log(f"设置脱水输出目录: {self.output_dir}")
            else:
                # 否则，使用选择的目录的同级目录"condensed"作为输出目录
                self.book_base_dir = parent_dir
                self.output_dir = os.path.join(parent_dir, "condensed")
                
                # 如果目录不存在，创建目录
                if not os.path.exists(self.output_dir):
                    try:
                        os.makedirs(self.output_dir)
                    except Exception as e:
                        QMessageBox.warning(self, "警告", f"无法创建脱水输出目录: {str(e)}")
                        # 如果创建失败，使用选择的目录作为输出目录
                        self.output_dir = dir_path
                
                self.output_dir_edit.setText(self.output_dir)
                self.add_log(f"设置脱水输出目录: {self.output_dir}")
    
    def browse_output_dir(self):
        """浏览并选择脱水输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择脱水输出目录", ""
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_dir_edit.setText(dir_path)
            self.add_log(f"已设置脱水输出目录: {dir_path}")
    
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
        
        # 更新章节范围
        if self.txt_files:
            self.end_chapter_spin.setValue(len(self.txt_files))
            
        # 添加日志
        self.add_log(f"已加载{len(self.txt_files)}个TXT文件")
    
    def start_condensing(self):
        """开始脱水处理"""
        # 检查API配置
        if not hasattr(config, 'GEMINI_API_CONFIG') or not config.GEMINI_API_CONFIG:
            # 尝试加载API配置
            if not config.load_api_config():
                # 如果加载失败，则显示警告
                QMessageBox.warning(self, "API配置缺失", 
                                  "未找到有效的API密钥配置。请先在设置中配置API密钥。")
                return
        
        # 检查是否已初始化API密钥管理器
        if not hasattr(main_module, 'gemini_key_manager') or main_module.gemini_key_manager is None:
            # 尝试初始化API密钥管理器
            try:
                main_module.gemini_key_manager = key_manager.APIKeyManager(
                    config.GEMINI_API_CONFIG,
                    config.DEFAULT_MAX_RPM
                )
            except Exception as e:
                QMessageBox.warning(self, "API密钥管理器初始化失败",
                                  f"无法初始化API密钥管理器: {str(e)}")
                return
        
        # 检查输入参数
        folder_path = self.folder_path_edit.text()
        
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "错误", "请选择有效的TXT文件夹")
            return
        
        if not self.txt_files:
            QMessageBox.warning(self, "错误", "所选文件夹中未找到TXT文件")
            return
        
        if not self.output_dir or not os.path.exists(self.output_dir):
            QMessageBox.warning(self, "错误", "请选择有效的脱水输出目录")
            return
            
        # 准备参数
        args = {
            'input_files': self.txt_files,
            'start_chapter': self.start_chapter_spin.value(),
            'end_chapter': self.end_chapter_spin.value(),
            'output_dir': self.output_dir,
            'force_regenerate': self.force_regenerate_checkbox.isChecked()  # 添加强制生成选项
        }
        
        # 创建并启动工作线程
        self.worker_thread = WorkerThread('condense', args)
        self.worker_thread.update_progress.connect(self.update_progress)
        self.worker_thread.operation_complete.connect(self.operation_complete)
        self.worker_thread.log_message.connect(self.add_log)
        
        # 更新UI状态
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在脱水处理...")
        
        # 添加开始日志
        self.add_log(f"开始脱水处理，章节范围: {self.start_chapter_spin.value()} - {self.end_chapter_spin.value()}")
        self.add_log(f"脱水输出目录: {self.output_dir}")
        self.add_log(f"强制生成模式: {'开启' if self.force_regenerate_checkbox.isChecked() else '关闭'}")
        
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
            self.status_label.setText("脱水完成")
            self.add_log("脱水处理成功完成")
            
            # 创建带有两个按钮的自定义弹窗
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("操作完成")
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Information)
            
            # 添加"确定"按钮（留在当前页面）
            ok_button = msg_box.addButton("确定", QMessageBox.AcceptRole)
            
            # 添加"合并成EPUB"按钮（跳转到转EPUB页面）
            epub_button = msg_box.addButton("合并成EPUB", QMessageBox.ActionRole)
            
            # 显示弹窗并等待用户操作
            msg_box.exec_()
            
            # 根据用户选择的按钮执行相应操作
            if msg_box.clickedButton() == epub_button:
                # 发送脱水完成信号，传递书名目录和脱水结果目录
                self.condense_complete.emit(self.book_base_dir, self.output_dir)
            # 如果点击确定按钮，不执行任何操作（留在当前页面）
        else:
            self.status_label.setText("脱水失败")
            self.add_log(f"脱水处理失败: {message}")
            QMessageBox.critical(self, "操作失败", message)
            
    def toggle_line_wrap(self, state):
        """切换自动换行选项"""
        if state == Qt.Checked:
            self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.log_text.setLineWrapMode(QTextEdit.NoWrap) 