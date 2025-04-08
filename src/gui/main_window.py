#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的主窗口类
"""

import os
import sys
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, 
                            QVBoxLayout, QWidget, QLabel, QHBoxLayout, QFrame)
from PyQt5.QtCore import QSize, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from ctypes import windll, c_int, byref, sizeof

# 导入版本信息（添加更健壮的错误处理）
VERSION_STRING = "AI小说工具"  # 默认版本字符串，如果无法导入版本模块则使用此值
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
from .resources import get_icon
from .style import get_material_style  # 导入样式表函数

class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 定义信号，用于标签页之间传递路径信息
    split_path_changed = pyqtSignal(str, str)  # 发送(书名目录, 分割结果目录)
    condense_path_changed = pyqtSignal(str, str)  # 发送(书名目录, 脱水结果目录)
    
    def __init__(self):
        super().__init__()
        # 设置窗口样式
        self.setWindowFlags(self.windowFlags())
        
        self.init_ui()
        self.setup_connections()
        
        # 在Windows上启用暗色标题栏
        if hasattr(windll, 'dwmapi'):
            # Windows 10 1809或更高版本
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            windll.dwmapi.DwmSetWindowAttribute(
                int(self.winId()),
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                byref(c_int(2)),
                sizeof(c_int)
            )
        
        # 如果运行在打包环境中，确保正确应用样式
        if getattr(sys, 'frozen', False):
            self.ensure_style_applied()
    
    def ensure_style_applied(self):
        """确保在打包环境中正确应用样式表"""
        try:
            print("在打包环境中重新应用样式...")
            # 重新应用主样式表
            self.setStyleSheet(get_material_style())
            
            # 确保首页的卡片有正确的背景色
            if hasattr(self, 'home_tab'):
                # 添加额外的样式到首页
                self.home_tab.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    background-color: transparent;
                }
                #materialCard {
                    background-color: #2D2D2D;
                }
                QLabel[title="true"] {
                    color: #FFFFFF;
                    font-weight: bold;
                }
                """)
                
                # 遍历首页中的所有卡片，确保标题和描述文本可见
                for card in self.home_tab.findChildren(QFrame, "materialCard"):
                    for label in card.findChildren(QLabel):
                        label.setStyleSheet("color: #FFFFFF; background-color: transparent;")
                
            print("样式重新应用完成")
        except Exception as e:
            print(f"应用样式时出错: {e}")
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle(VERSION_STRING)
        self.setMinimumSize(900, 650)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标签页控件
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.setDocumentMode(True)  # 使用更现代的文档模式外观
        self.tabs.setTabPosition(QTabWidget.North)
        
        # 创建五个标签页
        self.home_tab = HomeTab()
        self.home_tab.setObjectName("home_tab")
        self.epub_splitter_tab = EpubSplitterTab()
        self.epub_splitter_tab.setObjectName("epub_splitter_tab")
        self.condenser_tab = CondenserTab()
        self.condenser_tab.setObjectName("condenser_tab")
        self.txt_to_epub_tab = TxtToEpubTab()
        self.txt_to_epub_tab.setObjectName("txt_to_epub_tab")
        self.api_test_tab = ApiTestTab()
        self.api_test_tab.setObjectName("api_test_tab")
        
        # 添加标签页到标签页控件，并设置图标
        self.tabs.addTab(self.home_tab, get_icon('home'), "首页")
        self.tabs.addTab(self.epub_splitter_tab, get_icon('book'), "EPUB转TXT")
        self.tabs.addTab(self.condenser_tab, get_icon('water'), "脱水处理")
        self.tabs.addTab(self.txt_to_epub_tab, get_icon('convert'), "TXT转EPUB")
        self.tabs.addTab(self.api_test_tab, get_icon('test'), "API测试")
        
        # 设置标签页图标大小
        self.tabs.setIconSize(QSize(20, 20))
        
        # 添加标签页控件到主布局
        main_layout.addWidget(self.tabs)
        
        # 创建并设置状态栏
        status_bar = QStatusBar()
        status_bar.setStyleSheet("color: #B0B0B0;")
        self.setStatusBar(status_bar)
        status_bar.showMessage(VERSION_STRING)
        
        # 设置中央控件
        self.setCentralWidget(central_widget)
        
        # 设置窗口样式
        self.setObjectName("mainWindow")
        self.setWindowIcon(get_icon('book'))
        
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
        
        # 标签页切换信号
        self.tabs.currentChanged.connect(self.on_tab_changed)
    
    def on_split_complete(self, base_dir, output_dir):
        """EPUB分割完成后的处理"""
        # 发送信号，通知脱水处理标签页
        self.split_path_changed.emit(base_dir, output_dir)
        
        # 自动切换到脱水处理标签页
        self.tabs.setCurrentIndex(2)  # 索引2对应脱水处理标签页
        
        # 更新状态栏
        self.statusBar().showMessage(f"EPUB分割完成，已保存到: {output_dir}")
    
    def on_condense_complete(self, base_dir, output_dir):
        """脱水处理完成后的处理"""
        # 发送信号，通知TXT转EPUB标签页
        self.condense_path_changed.emit(base_dir, output_dir)
        
        # 自动切换到TXT转EPUB标签页（只有在用户点击了"合并成EPUB"按钮时才会触发）
        self.tabs.setCurrentIndex(3)  # 索引3对应TXT转EPUB标签页
        
        # 更新状态栏
        self.statusBar().showMessage(f"脱水处理完成，已保存到: {output_dir}")
    
    def on_tab_changed(self, index):
        """标签页切换时的处理"""
        tab_names = ["首页", "EPUB转TXT", "脱水处理", "TXT转EPUB", "API测试"]
        if 0 <= index < len(tab_names):
            self.statusBar().showMessage(f"当前功能: {tab_names[index]}")
    
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