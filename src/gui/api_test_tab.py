#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API测试标签页 - 简单测试配置文件中的API连接状态
"""

import json
import os
import sys
import requests
import threading
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QGroupBox, QTableWidget, 
                           QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor
from pathlib import Path
import re

# API配置
GEMINI_API_CONFIG = []
OPENAI_API_CONFIG = []

# 查找配置文件路径
def get_base_dir():
    """获取基础目录路径，确保兼容不同的目录结构"""
    # 当前文件所在目录
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 从 src/gui 推断项目根目录
    if os.path.basename(os.path.dirname(current_file_dir)) == 'src':
        # src/gui 结构
        return Path(os.path.dirname(os.path.dirname(current_file_dir)))
    
    # 如果是打包的exe
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        return Path(exe_dir)
    
    # 默认返回当前目录的上两级
    return Path(os.path.dirname(os.path.dirname(current_file_dir)))

def get_config_file_path():
    """获取配置文件路径"""
    base_dir = get_base_dir()
    
    # 按优先级检查配置文件位置
    possible_paths = [
        os.path.join(base_dir, "api_keys.json"),
        os.path.join(base_dir, "config", "api_keys.json"),
    ]
    
    # 如果是打包的exe，优先检查exe所在目录
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        possible_paths.insert(0, os.path.join(exe_dir, "api_keys.json"))
    
    print(f"可能的配置文件路径:")
    for path in possible_paths:
        exists = os.path.exists(path)
        print(f"  - {path} {'(存在)' if exists else '(不存在)'}")
        if exists:
            return path
    
    # 默认返回第一个路径
    return possible_paths[0]

def load_api_config():
    """加载API配置
    
    Returns:
        bool: 配置加载是否成功
    """
    global GEMINI_API_CONFIG, OPENAI_API_CONFIG
    
    config_file_path = get_config_file_path()
    print(f"使用配置文件路径: {config_file_path}")
    
    if not os.path.exists(config_file_path):
        print(f"配置文件不存在: {config_file_path}")
        return False
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            
        # 加载Gemini API配置
        if 'gemini_api' in config_data and isinstance(config_data['gemini_api'], list):
            GEMINI_API_CONFIG = config_data['gemini_api']
            print(f"已加载 {len(GEMINI_API_CONFIG)} 个Gemini API配置")
        
        # 加载OpenAI API配置
        if 'openai_api' in config_data and isinstance(config_data['openai_api'], list):
            OPENAI_API_CONFIG = config_data['openai_api']
            print(f"已加载 {len(OPENAI_API_CONFIG)} 个OpenAI API配置")
            
        # 至少有一种API配置加载成功即可
        return len(GEMINI_API_CONFIG) > 0 or len(OPENAI_API_CONFIG) > 0
            
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        
    return False 

# 初始加载配置
load_api_config()

class ApiTestSignals(QObject):
    """API测试信号类"""
    test_complete = pyqtSignal(str, bool, str)  # API标识, 是否通过, 错误信息

class ApiTestTab(QWidget):
    """API测试标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 打印当前环境信息
        print(f"当前工作目录: {os.getcwd()}")
        print(f"是否打包为exe: {getattr(sys, 'frozen', False)}")
        if getattr(sys, 'frozen', False):
            print(f"exe路径: {sys.executable}")
            print(f"exe目录: {os.path.dirname(sys.executable)}")
        
        self.signals = ApiTestSignals()
        self.signals.test_complete.connect(self.on_test_complete)
        
        # 添加测试状态跟踪变量
        self.testing_all = False        # 是否正在进行"测试全部"操作
        self.total_tests = 0            # 当前测试批次中的总测试数量
        self.completed_tests = 0        # 当前批次中已完成的测试数量
        self.test_queue = []            # 测试队列，存储待测试的API信息
        
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 创建说明标签
        info_label = QLabel("此功能用于测试配置文件中的API密钥是否有效。\n"
                             "点击'测试全部'按钮可以一次性测试所有API，或者点击各API右侧的'测试'按钮单独测试。")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # 创建配置文件路径显示
        config_path_label = QLabel(f"配置文件: {get_config_file_path()}")
        config_path_label.setStyleSheet("color: #666666; font-size: 10px;")
        main_layout.addWidget(config_path_label)
        
        # 创建按钮组
        button_layout = QHBoxLayout()
        self.test_all_button = QPushButton("测试全部API")
        self.test_all_button.clicked.connect(self.test_all_apis)
        self.reload_button = QPushButton("重新加载配置")
        self.reload_button.clicked.connect(self.reload_api_keys)
        
        button_layout.addWidget(self.test_all_button)
        button_layout.addWidget(self.reload_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 添加进度标签
        self.progress_label = QLabel("")
        main_layout.addWidget(self.progress_label)
        self.progress_label.hide()  # 初始隐藏进度标签
        
        # 创建API列表表格
        self.api_table = QTableWidget()
        self.api_table.setColumnCount(4)
        self.api_table.setHorizontalHeaderLabels(["API类型", "模型", "状态", "操作"])
        self.api_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.api_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.api_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        main_layout.addWidget(self.api_table)
        
        self.setLayout(main_layout)
        
        # 加载API密钥
        self.load_api_list()
    
    def create_test_button(self, api_type, index):
        """创建测试按钮，并正确设置其回调函数"""
        button = QPushButton("测试")
        
        # 创建一个特定的调用函数，避免lambda捕获问题
        def on_test_clicked(checked=False, a_type=api_type, idx=index):
            # 获取按钮所在的表格行
            for row in range(self.api_table.rowCount()):
                if self.api_table.cellWidget(row, 3) == button:
                    self.test_api(a_type, idx, row)
                    break
            else:
                # 如果未找到对应行，使用-1表示未知行
                self.test_api(a_type, idx, -1)
        
        button.clicked.connect(on_test_clicked)
        return button
    
    def load_api_list(self):
        """从配置文件加载API列表并显示在表格中"""
        self.api_table.setRowCount(0)  # 清空表格
        
        # 打印当前配置状态
        print(f"Gemini API配置数量: {len(GEMINI_API_CONFIG)}")
        print(f"OpenAI API配置数量: {len(OPENAI_API_CONFIG)}")
        
        row = 0
        api_count = 0
        
        # 存储已添加的API标识符，避免重复
        added_apis = set()
        
        # 添加Gemini API
        for i, api in enumerate(GEMINI_API_CONFIG):
            if not isinstance(api, dict) or "key" not in api:
                print(f"跳过无效的gemini_api配置 #{i}: {api}")
                continue
            
            model_name = api.get("model", "未指定")
            # 使用重定向URL和密钥前缀创建更具唯一性的标识符
            redirect_url = api.get("redirect_url", "")
            key_prefix = api.get("key", "")[:8] if api.get("key") else ""
            
            # 创建唯一标识符：类型+模型+URL域名+密钥前缀
            url_domain = ""
            try:
                if redirect_url:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(redirect_url)
                    url_domain = parsed_url.netloc
            except:
                url_domain = "unknown"
                
            api_identifier = f"Gemini:{model_name}:{url_domain}:{key_prefix}"
            
            # 检查是否已添加过相同的API
            if api_identifier in added_apis:
                print(f"跳过重复的API: {api_identifier}")
                continue
            
            added_apis.add(api_identifier)
            api_count += 1
            
            print(f"添加Gemini API #{i}, 模型: {model_name}, 域名: {url_domain}")
            self.api_table.insertRow(row)
            
            # API类型
            api_type_item = QTableWidgetItem("Gemini")
            api_type_item.setFlags(api_type_item.flags() & ~Qt.ItemIsEditable)
            self.api_table.setItem(row, 0, api_type_item)
            
            # 模型 - 增强显示，添加来源域名
            # 创建增强版的模型显示文本
            display_model_name = model_name
            if url_domain:
                # 从完整域名中提取简短的来源名称
                source_name = url_domain.split('.')[0] if '.' in url_domain else url_domain
                # 对于googleapis，使用更友好的名称
                if source_name == "generativelanguage" and "googleapis" in url_domain:
                    source_name = "官方API"
                display_model_name = f"{model_name} ({source_name})"
            
            model_item = QTableWidgetItem(display_model_name)
            model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
            # 存储原始模型名作为item的数据，供搜索和匹配使用
            model_item.setData(Qt.UserRole, model_name)
            self.api_table.setItem(row, 1, model_item)
            
            # 状态
            status_item = QTableWidgetItem("未测试")
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            self.api_table.setItem(row, 2, status_item)
            
            # 测试按钮
            test_button = self.create_test_button("gemini", i)
            self.api_table.setCellWidget(row, 3, test_button)
            
            row += 1
        
        # 添加OpenAI API (如果存在)
        for i, api in enumerate(OPENAI_API_CONFIG):
            if not isinstance(api, dict) or "key" not in api:
                print(f"跳过无效的openai_api配置 #{i}: {api}")
                continue
            
            model_name = api.get("model", "未指定")
            # 使用重定向URL和密钥前缀创建更具唯一性的标识符
            redirect_url = api.get("redirect_url", "")
            key_prefix = api.get("key", "")[:8] if api.get("key") else ""
            
            # 创建唯一标识符：类型+模型+URL域名+密钥前缀
            url_domain = ""
            try:
                if redirect_url:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(redirect_url)
                    url_domain = parsed_url.netloc
            except:
                url_domain = "unknown"
                
            api_identifier = f"OpenAI:{model_name}:{url_domain}:{key_prefix}"
            
            # 检查是否已添加过相同的API
            if api_identifier in added_apis:
                print(f"跳过重复的API: {api_identifier}")
                continue
            
            added_apis.add(api_identifier)
            api_count += 1
            
            print(f"添加OpenAI API #{i}, 模型: {model_name}, 域名: {url_domain}")
            self.api_table.insertRow(row)
            
            # API类型
            api_type_item = QTableWidgetItem("OpenAI")
            api_type_item.setFlags(api_type_item.flags() & ~Qt.ItemIsEditable)
            self.api_table.setItem(row, 0, api_type_item)
            
            # 模型 - 增强显示，添加来源域名
            # 创建增强版的模型显示文本
            display_model_name = model_name
            if url_domain:
                # 从完整域名中提取简短的来源名称
                source_name = url_domain.split('.')[0] if '.' in url_domain else url_domain
                # 对于openai官方API，使用更友好的名称
                if source_name == "api" and "openai.com" in url_domain:
                    source_name = "官方API"
                display_model_name = f"{model_name} ({source_name})"
            
            model_item = QTableWidgetItem(display_model_name)
            model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
            # 存储原始模型名作为item的数据，供搜索和匹配使用
            model_item.setData(Qt.UserRole, model_name)
            self.api_table.setItem(row, 1, model_item)
            
            # 状态
            status_item = QTableWidgetItem("未测试")
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            self.api_table.setItem(row, 2, status_item)
            
            # 测试按钮
            test_button = self.create_test_button("openai", i)
            self.api_table.setCellWidget(row, 3, test_button)
            
            row += 1
        
        print(f"总共添加了 {api_count} 个API, 行数: {row}")
        
        # 如果没有API配置，添加提示行
        if api_count == 0:
            self.api_table.insertRow(0)
            no_api_item = QTableWidgetItem("未找到API配置，请在api_keys.json文件中添加配置")
            no_api_item.setFlags(no_api_item.flags() & ~Qt.ItemIsEditable)
            self.api_table.setItem(0, 0, no_api_item)
            self.api_table.setSpan(0, 0, 1, 4)  # 合并单元格
        
        # 调整表格行高
        for i in range(self.api_table.rowCount()):
            self.api_table.setRowHeight(i, 40)
    
    def reload_api_keys(self):
        """重新加载API密钥配置"""
        # 重新加载配置
        load_api_config()
        print(f"重新加载配置完成")
        
        # 更新配置文件路径显示
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i).widget()
            if isinstance(item, QLabel) and item.text().startswith("配置文件:"):
                item.setText(f"配置文件: {get_config_file_path()}")
                break
        
        # 刷新API列表
        self.load_api_list()
    
    def test_all_apis(self):
        """测试所有API - 改进版，使用任务队列确保所有测试都能执行"""
        # 如果已经在测试中，不执行新的测试批次
        if self.testing_all:
            print("已有测试正在进行中，请等待完成")
            return
            
        # 设置测试状态
        self.testing_all = True
        self.test_queue = []  # 清空测试队列
        self.completed_tests = 0
        
        # 禁用测试按钮
        self.test_all_button.setEnabled(False)
        self.test_all_button.setText("测试中...")
        
        # 收集所有需要测试的API
        for row in range(self.api_table.rowCount()):
            # 跳过非API行（如提示行）
            if not self.api_table.cellWidget(row, 3):
                continue
                
            # 获取API类型和索引
            api_type = "gemini" if self.api_table.item(row, 0).text() == "Gemini" else "openai"
            
            # 从UserRole数据中获取原始模型名称
            model_item = self.api_table.item(row, 1)
            if not model_item:
                continue
                
            model_name = model_item.data(Qt.UserRole) or model_item.text()
            
            # 从显示文本中提取原始模型名称（如果没有存储在UserRole中）
            if not model_name and "(" in model_item.text():
                model_name = model_item.text().split(" (")[0]
            
            # 查找对应的API配置索引
            config_list = GEMINI_API_CONFIG if api_type == "gemini" else OPENAI_API_CONFIG
            
            found_matching_api = False
            for i, api in enumerate(config_list):
                if api.get("model", "未指定") == model_name:
                    # 将此API添加到测试队列，包含表格行索引
                    # 元组格式: (api_type, config_index, table_row_index)
                    self.test_queue.append((api_type, i, row))
                    
                    # 更新状态
                    status_item = self.api_table.item(row, 2)
                    if status_item:
                        status_item.setText("等待测试...")
                        status_item.setBackground(QColor(255, 255, 0, 100))  # 半透明黄色
                    # 禁用单个测试按钮
                    if self.api_table.cellWidget(row, 3):
                        self.api_table.cellWidget(row, 3).setEnabled(False)
                    
                    found_matching_api = True
                    break
            
            # 如果没有找到匹配的API配置，标记为"配置缺失"
            if not found_matching_api:
                status_item = self.api_table.item(row, 2)
                if status_item:
                    status_item.setText("配置缺失")
                    status_item.setBackground(QColor(255, 165, 0, 100))  # 半透明橙色
        
        # 设置总测试数量
        self.total_tests = len(self.test_queue)
        
        # 显示和更新进度标签
        self._update_test_progress()
        
        if self.total_tests == 0:
            # 没有找到任何API，恢复测试按钮
            self.test_all_button.setEnabled(True)
            self.test_all_button.setText("测试全部API")
            self.testing_all = False
            self.progress_label.setText("没有找到可测试的API")
            self.progress_label.show()
            return
        
        # 启动第一批测试（最多同时测试5个API）
        self._start_next_tests(min(5, self.total_tests))
    
    def _start_next_tests(self, count=1):
        """从队列中启动下一批测试
        
        Args:
            count: 要启动的测试数量
        """
        tests_started = 0
        
        # 启动指定数量的测试，或直到队列为空
        while tests_started < count and self.test_queue:
            api_type, index, row_index = self.test_queue.pop(0)
            self.test_api(api_type, index, row_index)
            tests_started += 1
    
    def _update_test_progress(self):
        """更新测试进度显示"""
        if self.total_tests > 0:
            progress_text = f"测试进度: {self.completed_tests}/{self.total_tests}"
            if self.completed_tests < self.total_tests:
                queue_left = len(self.test_queue)
                running = self.total_tests - self.completed_tests - queue_left
                progress_text += f" (运行中: {running}, 等待: {queue_left})"
            self.progress_label.setText(progress_text)
            self.progress_label.show()
        else:
            self.progress_label.hide()
    
    def test_api(self, api_type, index, row_index=-1):
        """测试指定的API
        
        Args:
            api_type: API类型 ("gemini" 或 "openai")
            index: API配置索引
            row_index: 表格行索引，用于直接更新状态
        """
        # 获取API信息
        api_key = ""
        api_model = ""
        api_id = f"{api_type}_{index}_{row_index}"  # 在API ID中包含行索引
        
        if api_type == "gemini" and index < len(GEMINI_API_CONFIG):
            api_info = GEMINI_API_CONFIG[index]
            api_key = api_info.get("key", "")
            api_model = api_info.get("model", "gemini-pro")
        elif api_type == "openai" and index < len(OPENAI_API_CONFIG):
            api_info = OPENAI_API_CONFIG[index]
            api_key = api_info.get("key", "")
            api_model = api_info.get("model", "gpt-3.5-turbo")
        else:
            self.signals.test_complete.emit(api_id, False, "API配置无效")
            return
        
        # 更新状态为"测试中"
        if row_index >= 0 and row_index < self.api_table.rowCount():
            # 如果提供了有效的行索引，直接更新该行
            status_item = self.api_table.item(row_index, 2)
            if status_item:
                status_item.setText("测试中...")
                status_item.setBackground(QColor(173, 216, 230, 100))  # 半透明浅蓝色
            # 禁用测试按钮
            if self.api_table.cellWidget(row_index, 3):
                self.api_table.cellWidget(row_index, 3).setEnabled(False)
        else:
            # 否则使用原来的查找逻辑
            for row in range(self.api_table.rowCount()):
                api_type_text = self.api_table.item(row, 0).text()
                model_item = self.api_table.item(row, 1)
                if not model_item:
                    continue
                    
                api_model_text = model_item.text()
                
                if ((api_type == "gemini" and api_type_text == "Gemini") or 
                    (api_type == "openai" and api_type_text == "OpenAI")):
                    
                    # 从UserRole数据中获取原始模型名称
                    model_name = model_item.data(Qt.UserRole) or model_item.text()
                    
                    # 从显示文本中提取原始模型名称（如果没有存储在UserRole中）
                    if not model_name and "(" in model_item.text():
                        model_name = model_item.text().split(" (")[0]
                    
                    if model_name == api_model:
                        status_item = self.api_table.item(row, 2)
                        if status_item:
                            status_item.setText("测试中...")
                            status_item.setBackground(QColor(173, 216, 230, 100))  # 半透明浅蓝色
                        # 禁用测试按钮
                        if self.api_table.cellWidget(row, 3):
                            self.api_table.cellWidget(row, 3).setEnabled(False)
                        break
        
        # 在后台线程中测试API连接
        thread = threading.Thread(target=self._test_api_connection, 
                                args=(api_id, api_type, api_key, api_model))
        thread.daemon = True
        thread.start()
    
    def _test_api_connection(self, api_id, api_type, api_key, api_model):
        """在后台线程中测试API连接，参考api_service.py的实现"""
        try:
            # 从api_id中提取API索引和行索引
            parts = api_id.split("_")
            if len(parts) == 3:  # 新格式: type_index_row
                api_index = int(parts[1])
                row_index = int(parts[2])
            else:  # 旧格式兼容: type_index
                api_index = int(parts[1])
                row_index = -1
            
            if api_type == "gemini":
                # 测试Gemini API
                # 获取更多参数
                api_config = None
                
                # 确保索引有效，防止索引越界
                if 0 <= api_index < len(GEMINI_API_CONFIG):
                    api_config = GEMINI_API_CONFIG[api_index]
                else:
                    self.signals.test_complete.emit(api_id, False, "API配置无效：索引超出范围")
                    return
                    
                redirect_url = api_config.get('redirect_url', '')
                
                # 构建正确的API URL格式
                # 优先使用配置的redirect_url，如果没有则使用默认URL
                final_api_url = ""
                
                # 针对官方Google API的正规URL格式
                if redirect_url:
                    # 使用配置的重定向URL
                    final_api_url = redirect_url
                    
                    # 如果URL不包含:generateContent后缀，添加模型和方法
                    if ":generateContent" not in final_api_url:
                        # 确保URL末尾有斜杠
                        if not final_api_url.endswith('/'):
                            final_api_url += '/'
                        
                        # 添加模型名和方法
                        final_api_url += f"{api_model}:generateContent"
                else:
                    # 使用默认URL
                    final_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent"
                
                # 构建请求头
                headers = {
                    "Content-Type": "application/json"
                }
                
                # 处理API密钥参数
                if "key=" not in final_api_url:
                    # 如果URL中没有key参数，根据不同情况处理
                    if "aliyahzombie" in redirect_url:
                        # 使用自定义标头
                        headers["x-goog-api-key"] = api_key
                    elif redirect_url and "generativelanguage.googleapis.com" not in redirect_url:
                        # 对于非官方Google API，添加到请求头
                        headers["x-goog-api-key"] = api_key
                    else:
                        # 对于官方Google API，添加到URL
                        if "?" in final_api_url:
                            final_api_url += f"&key={api_key}"
                        else:
                            final_api_url += f"?key={api_key}"
                
                # 打印请求信息，帮助诊断
                print(f"Gemini API测试URL: {final_api_url}")
                
                # 构建请求体
                request_data = {
                    "contents": [
                        {
                            "parts": [
                                {"text": "你好，这是API测试消息。请用一句话回复。"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 50
                    }
                }
                
                # 打印请求信息，帮助诊断
                print(f"请求头: {headers}")
                print(f"请求体示例: {json.dumps(request_data, ensure_ascii=False)[:100]}...")
                
                try:
                    # 发送请求
                    response = requests.post(final_api_url, headers=headers, json=request_data, timeout=30)
                    response.raise_for_status()  # 这会在HTTP错误时抛出异常
                    
                    # 检查响应是否包含预期的结构
                    resp_json = response.json()
                    print(f"响应状态码: {response.status_code}")
                    print(f"响应头: {response.headers}")
                    print(f"响应体示例: {json.dumps(resp_json, ensure_ascii=False)[:100]}...")
                    
                    # 增强的响应检测逻辑，支持多种不同的响应格式
                    success = False
                    
                    # 标准Gemini格式
                    if "candidates" in resp_json and len(resp_json["candidates"]) > 0:
                        success = True
                    
                    # 一些第三方API使用不同的响应格式
                    elif "response" in resp_json:
                        success = True
                    
                    # 某些代理使用output字段
                    elif "output" in resp_json:
                        success = True
                    
                    # 某些API直接返回内容数组
                    elif "results" in resp_json:
                        success = True
                    
                    # 某些API将结果封装在data字段中
                    elif "data" in resp_json:
                        data = resp_json["data"]
                        if isinstance(data, dict) and ("candidates" in data or "content" in data):
                            success = True
                    
                    # 某些API使用content作为直接返回
                    elif "content" in resp_json:
                        success = True
                    
                    # 有效响应
                    if success:
                        self.signals.test_complete.emit(api_id, True, "")
                    else:
                        # 如果没有找到有效结构，但HTTP响应是200，认为是成功的
                        if response.status_code == 200:
                            print("没有找到标准的响应字段，但HTTP状态为200，认为API可用")
                            self.signals.test_complete.emit(api_id, True, "")
                        else:
                            self.signals.test_complete.emit(api_id, False, "API响应格式不正确，未找到有效的响应字段")
                except requests.exceptions.HTTPError as e:
                    error_msg = str(e)
                    status_code = e.response.status_code if hasattr(e, 'response') else "未知"
                    
                    # 尝试获取更详细的错误信息
                    try:
                        error_text = e.response.text
                        print(f"错误响应: {error_text}")
                        error_json = e.response.json()
                        print(f"错误JSON: {json.dumps(error_json, ensure_ascii=False)}")
                        if "error" in error_json:
                            if "message" in error_json["error"]:
                                error_msg = error_json["error"]["message"]
                            elif "msg" in error_json["error"]:
                                error_msg = error_json["error"]["msg"]
                    except:
                        pass
                        
                    self.signals.test_complete.emit(api_id, False, f"HTTP错误 {status_code}: {error_msg}")
                    return
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                       requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    # 统一处理常见异常
                    error_type = type(e).__name__
                    self.signals.test_complete.emit(api_id, False, f"{error_type}: {str(e)}")
                    return
            
            elif api_type == "openai":
                # 测试OpenAI API
                # 获取更多参数
                api_config = None
                
                # 确保索引有效，防止索引越界
                if 0 <= api_index < len(OPENAI_API_CONFIG):
                    api_config = OPENAI_API_CONFIG[api_index]
                else:
                    self.signals.test_complete.emit(api_id, False, "API配置无效：索引超出范围")
                    return
                    
                redirect_url = api_config.get('redirect_url', '')
                
                # 构建正确的API URL格式 - 避免添加额外的路径
                if redirect_url:
                    # 使用提供的redirect_url作为完整URL
                    final_api_url = redirect_url.strip()
                    print(f"原始redirect_url: {redirect_url}")
                    
                    # 检查URL是否已经包含chat/completions路径
                    if 'chat/completions' in final_api_url:
                        # URL已经包含了必要的路径，确保没有末尾斜杠
                        if final_api_url.endswith('/') and not final_api_url.endswith('/?'):
                            # 移除末尾的斜杠（但保留查询字符串中的斜杠）
                            final_api_url = final_api_url.rstrip('/')
                    else:
                        # URL不包含必要的路径，需要添加
                        # 首先移除末尾的斜杠（如果有）
                        final_api_url = final_api_url.rstrip('/')
                        # 添加chat/completions路径
                        final_api_url += '/chat/completions'
                else:
                    # 使用官方OpenAI端点
                    final_api_url = "https://api.openai.com/v1/chat/completions"
                
                print(f"最终OpenAI API测试URL: {final_api_url}")
                
                # 构建OpenAI格式的请求体
                request_data = {
                    "model": api_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": "你好，这是API测试消息。请用一句话回复。"
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 50
                }
                
                # 构建请求头
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                
                # 添加基本的User-Agent，提高兼容性
                headers["User-Agent"] = "Mozilla/5.0 OpenAI API Test Client"
                
                # 打印请求信息，帮助诊断
                print(f"请求URL: {final_api_url}")
                print(f"请求头: {headers}")
                print(f"请求体: {json.dumps(request_data, ensure_ascii=False)}")
                
                try:
                    # 对于第三方API增加超时时间，它们通常响应较慢
                    timeout = 60 if redirect_url and not "openai.com" in redirect_url else 30
                    print(f"设置请求超时: {timeout}秒")
                    
                    response = requests.post(final_api_url, headers=headers, json=request_data, timeout=timeout)
                    response.raise_for_status()  # 这会在HTTP错误时抛出异常
                    
                    # 检查响应是否包含预期的结构
                    resp_json = response.json()
                    print(f"响应状态码: {response.status_code}")
                    print(f"响应头: {response.headers}")
                    print(f"响应体示例: {json.dumps(resp_json, ensure_ascii=False)[:100]}...")
                    
                    # 增强的响应检测逻辑，支持多种不同的响应格式
                    success = False
                    
                    # 标准OpenAI格式
                    if "choices" in resp_json and len(resp_json["choices"]) > 0:
                        success = True
                    
                    # 一些第三方API使用不同的响应格式
                    elif "response" in resp_json:
                        success = True
                    
                    # 某些代理使用output字段
                    elif "output" in resp_json:
                        success = True
                    
                    # 某些API直接返回内容数组
                    elif "results" in resp_json:
                        success = True
                    
                    # 某些API将结果封装在data字段中
                    elif "data" in resp_json:
                        data = resp_json["data"]
                        if isinstance(data, dict) and ("choices" in data or "content" in data):
                            success = True
                    
                    # 某些API使用content作为直接返回
                    elif "content" in resp_json:
                        success = True
                    
                    # 有效响应
                    if success:
                        self.signals.test_complete.emit(api_id, True, "")
                    else:
                        # 如果没有找到有效结构，但HTTP响应是200，认为是成功的
                        if response.status_code == 200:
                            print("没有找到标准的响应字段，但HTTP状态为200，认为API可用")
                            self.signals.test_complete.emit(api_id, True, "")
                        else:
                            self.signals.test_complete.emit(api_id, False, "API响应格式不正确，未找到有效的响应字段")
                except requests.exceptions.HTTPError as e:
                    error_msg = str(e)
                    status_code = e.response.status_code if hasattr(e, 'response') else "未知"
                    
                    # 尝试获取更详细的错误信息
                    try:
                        error_text = e.response.text
                        print(f"错误响应: {error_text}")
                        error_json = e.response.json()
                        print(f"错误JSON: {json.dumps(error_json, ensure_ascii=False)}")
                        if "error" in error_json:
                            if "message" in error_json["error"]:
                                error_msg = error_json["error"]["message"]
                            elif "msg" in error_json["error"]:
                                error_msg = error_json["error"]["msg"]
                    except:
                        # 如果无法解析JSON，至少尝试获取响应文本
                        if hasattr(e, 'response') and hasattr(e.response, 'text'):
                            error_msg = f"{error_msg} - 响应: {e.response.text[:100]}"
                    
                    # 处理HTTP 404错误 - 可能是API路径不正确
                    if status_code == 404:
                        error_msg = f"API URL路径可能不正确({final_api_url})，请检查URL配置。错误: {error_msg}"
                    
                    self.signals.test_complete.emit(api_id, False, f"HTTP错误 {status_code}: {error_msg}")
                    return
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                       requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    # 统一处理常见异常
                    error_type = type(e).__name__
                    self.signals.test_complete.emit(api_id, False, f"{error_type}: {str(e)}")
                    return
            
            else:
                # 不支持的API类型
                self.signals.test_complete.emit(api_id, False, f"不支持的API类型: {api_type}")
                return
        
        except Exception as e:
            # 捕获所有未处理的异常，确保测试完成信号始终被发送
            import traceback
            print(f"API测试过程中发生未预期的异常: {str(e)}")
            print(traceback.format_exc())
            self.signals.test_complete.emit(api_id, False, f"测试出错: {str(e)}")
    
    def on_test_complete(self, api_id, success, error_message):
        """测试完成后的回调"""
        # 解析API ID
        parts = api_id.split("_")
        if len(parts) != 3:
            return
        
        api_type = parts[0]
        index = int(parts[1])
        row_index = int(parts[2])
        
        # 获取API信息
        api_info = None
        api_model = ""
        redirect_url = ""
        
        if api_type == "gemini" and index < len(GEMINI_API_CONFIG):
            api_info = GEMINI_API_CONFIG[index]
            api_model = api_info.get("model", "gemini-pro")
            redirect_url = api_info.get("redirect_url", "")
        elif api_type == "openai" and index < len(OPENAI_API_CONFIG):
            api_info = OPENAI_API_CONFIG[index]
            api_model = api_info.get("model", "gpt-3.5-turbo")
            redirect_url = api_info.get("redirect_url", "")
        
        # 获取API域名，用于更精确匹配
        url_domain = ""
        try:
            if redirect_url:
                from urllib.parse import urlparse
                parsed_url = urlparse(redirect_url)
                url_domain = parsed_url.netloc
        except:
            pass
        
        # 更新表格中的状态
        row_found = False
        if row_index >= 0 and row_index < self.api_table.rowCount():
            # 如果提供了有效的行索引，直接更新该行
            status_item = self.api_table.item(row_index, 2)
            if status_item:
                if success:
                    status_item.setText("测试通过")
                    status_item.setBackground(QColor(0, 255, 0, 100))  # 半透明绿色
                else:
                    status_text = "测试失败"
                    if error_message:
                        status_text += f": {error_message}"
                    status_item.setText(status_text)
                    status_item.setBackground(QColor(255, 0, 0, 100))  # 半透明红色
            
            # 重新启用测试按钮
            if self.api_table.cellWidget(row_index, 3):
                self.api_table.cellWidget(row_index, 3).setEnabled(True)
            
            row_found = True
        
        # 如果没有找到有效行，使用回退匹配逻辑
        if not row_found and api_model:
            for row in range(self.api_table.rowCount()):
                api_type_text = self.api_table.item(row, 0).text()
                model_item = self.api_table.item(row, 1)
                if not model_item:
                    continue
                
                # 从UserRole数据中获取原始模型名称
                model_name = model_item.data(Qt.UserRole) or model_item.text()
                
                # 从显示文本中提取原始模型名称（如果没有存储在UserRole中）
                if not model_name and "(" in model_item.text():
                    model_name = model_item.text().split(" (")[0]
                
                # 检查API类型和模型是否匹配
                type_matches = (api_type == "gemini" and api_type_text == "Gemini") or \
                              (api_type == "openai" and api_type_text == "OpenAI")
                
                model_matches = model_name == api_model
                
                # 如果有域名信息，则使用域名进一步确认匹配
                domain_matches = True
                if url_domain and "(" in model_item.text():
                    display_domain = model_item.text().split("(")[1].rstrip(")")
                    # 检查域名的第一部分是否匹配
                    domain_first_part = url_domain.split('.')[0] if '.' in url_domain else url_domain
                    if display_domain != "官方API" and display_domain != domain_first_part:
                        domain_matches = False
                
                if type_matches and model_matches and domain_matches:
                    # 更新状态
                    status_item = self.api_table.item(row, 2)
                    if status_item:
                        if success:
                            status_item.setText("测试通过")
                            status_item.setBackground(QColor(0, 255, 0, 100))  # 半透明绿色
                        else:
                            status_text = "测试失败"
                            if error_message:
                                status_text += f": {error_message}"
                            status_item.setText(status_text)
                            status_item.setBackground(QColor(255, 0, 0, 100))  # 半透明红色
                    
                    # 重新启用测试按钮
                    if self.api_table.cellWidget(row, 3):
                        self.api_table.cellWidget(row, 3).setEnabled(True)
                    
                    # 找到匹配的行后就不再继续查找
                    row_found = True
                    break
        
        # 如果始终找不到行，记录错误信息
        if not row_found:
            print(f"警告: 无法找到匹配的表格行更新API测试状态: {api_id}, 类型:{api_type}, 模型:{api_model}")
        
        # 如果是在"测试全部"模式中，更新计数并继续测试
        if self.testing_all:
            self.completed_tests += 1
            self._update_test_progress()
            
            # 如果还有待测试的API，启动下一个测试
            if self.test_queue:
                self._start_next_tests(1)
            
            # 检查是否所有测试都已完成
            if self.completed_tests >= self.total_tests:
                # 验证所有行状态是否正确更新
                self._verify_all_tests_complete()
                
                # 重置测试状态
                self.testing_all = False
                self.test_all_button.setEnabled(True)
                self.test_all_button.setText("测试全部API")
                self.progress_label.setText(f"测试完成: {self.completed_tests}/{self.total_tests}")
    
    def _verify_all_tests_complete(self):
        """验证是否所有测试行都已正确更新状态"""
        pending_rows = []
        
        # 查找所有显示为"等待测试..."的行
        for row in range(self.api_table.rowCount()):
            status_item = self.api_table.item(row, 2)
            if status_item and status_item.text() == "等待测试...":
                pending_rows.append(row)
        
        if pending_rows:
            print(f"发现 {len(pending_rows)} 行显示为'等待测试...'但测试队列已空")
            
            # 将这些行标记为"测试状态未知"
            for row in pending_rows:
                status_item = self.api_table.item(row, 2)
                if status_item:
                    status_item.setText("测试状态未知，请重试")
                    status_item.setBackground(QColor(255, 165, 0, 100))  # 半透明橙色
                
                # 重新启用测试按钮
                if self.api_table.cellWidget(row, 3):
                    self.api_table.cellWidget(row, 3).setEnabled(True) 