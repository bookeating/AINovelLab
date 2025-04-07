#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的主窗口类
"""

import os
import sys
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QStatusBar
from PyQt5.QtCore import QSize, pyqtSignal

# 导入版本信息（添加更健壮的错误处理）
VERSION_STRING = "AI小说实验室"  # 默认版本字符串，如果无法导入版本模块则使用此值
try:
    from ..version import get_version_string
    VERSION_STRING = get_version_string()
except ImportError:
    try:
        # 尝试其他导入路径
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from version import get_version_string
        VERSION_STRING = get_version_string()
    except ImportError:
        print("警告: 无法导入版本信息模块，将使用默认版本信息")
    except Exception as e:
        print(f"警告: 导入版本信息时发生错误: {e}")

from .home_tab import HomeTab
from .epub_splitter_tab import EpubSplitterTab
from .condenser_tab import CondenserTab
from .txt_to_epub_tab import TxtToEpubTab
from .api_test_tab import ApiTestTab

class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 定义信号，用于标签页之间传递路径信息
    split_path_changed = pyqtSignal(str, str)  # 发送(书名目录, 分割结果目录)
    condense_path_changed = pyqtSignal(str, str)  # 发送(书名目录, 脱水结果目录)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle(VERSION_STRING)
        self.setMinimumSize(800, 600)
        
        # 创建标签页控件
        self.tabs = QTabWidget()
        
        # 创建五个标签页
        self.home_tab = HomeTab()
        self.epub_splitter_tab = EpubSplitterTab()
        self.condenser_tab = CondenserTab()
        self.txt_to_epub_tab = TxtToEpubTab()
        self.api_test_tab = ApiTestTab()
        
        # 添加标签页到标签页控件
        self.tabs.addTab(self.home_tab, "首页")
        self.tabs.addTab(self.epub_splitter_tab, "EPUB转TXT")
        self.tabs.addTab(self.condenser_tab, "脱水处理")
        self.tabs.addTab(self.txt_to_epub_tab, "TXT转EPUB")
        self.tabs.addTab(self.api_test_tab, "API测试")
        
        # 设置中央控件
        self.setCentralWidget(self.tabs)
        
        # 创建并设置状态栏
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage(VERSION_STRING)
        
        # 显示窗口
        self.show()
    
    def setup_connections(self):
        """设置信号连接"""
        # 连接EPUB分割标签页的信号
        self.epub_splitter_tab.split_complete.connect(self.on_split_complete)
        
        # 连接脱水处理标签页的信号
        self.condenser_tab.condense_complete.connect(self.on_condense_complete)
        
        # 将主窗口信号连接到标签页
        self.split_path_changed.connect(self.condenser_tab.on_split_path_changed)
        self.condense_path_changed.connect(self.txt_to_epub_tab.on_condense_path_changed)
    
    def on_split_complete(self, base_dir, output_dir):
        """EPUB分割完成后的处理"""
        # 发送信号，通知脱水处理标签页
        self.split_path_changed.emit(base_dir, output_dir)
        
        # 可选：自动切换到脱水处理标签页
        self.tabs.setCurrentIndex(2)  # 索引2对应脱水处理标签页
    
    def on_condense_complete(self, base_dir, output_dir):
        """脱水处理完成后的处理"""
        # 发送信号，通知TXT转EPUB标签页
        self.condense_path_changed.emit(base_dir, output_dir)
        
        # 自动切换到TXT转EPUB标签页（只有在用户点击了"合并成EPUB"按钮时才会触发）
        self.tabs.setCurrentIndex(3)  # 索引3对应TXT转EPUB标签页
        
    def closeEvent(self, event):
        """关闭窗口事件处理函数，确保所有后台线程都被停止"""
        # 停止所有可能存在的工作线程
        if hasattr(self.epub_splitter_tab, 'worker_thread') and self.epub_splitter_tab.worker_thread:
            self.epub_splitter_tab.worker_thread.stop()
            self.epub_splitter_tab.worker_thread.wait(1000)  # 等待最多1秒让线程结束
            
        if hasattr(self.condenser_tab, 'worker_thread') and self.condenser_tab.worker_thread:
            self.condenser_tab.worker_thread.stop()
            self.condenser_tab.worker_thread.wait(1000)  # 等待最多1秒让线程结束
            
        if hasattr(self.txt_to_epub_tab, 'worker_thread') and self.txt_to_epub_tab.worker_thread:
            self.txt_to_epub_tab.worker_thread.stop()
            self.txt_to_epub_tab.worker_thread.wait(1000)  # 等待最多1秒让线程结束
            
        # 处理可能没有正常退出的线程
        # 注意：Python的线程无法直接强制终止，所以我们只能设置标志位并等待它们自己结束
        print("正在关闭所有工作线程...")
        
        # 接受关闭事件
        event.accept() 