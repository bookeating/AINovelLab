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
            self.test_api(a_type, idx)
        
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
        """测试所有API"""
        # 禁用测试按钮
        self.test_all_button.setEnabled(False)
        self.test_all_button.setText("测试中...")
        
        # 遍历表格中的所有行，点击对应的测试按钮
        for row in range(self.api_table.rowCount()):
            if self.api_table.cellWidget(row, 3):
                # 获取API类型和索引
                api_type = "gemini" if self.api_table.item(row, 0).text() == "Gemini" else "openai"
                
                # 遍历API配置查找匹配的索引
                # 从UserRole数据中获取原始模型名称
                model_item = self.api_table.item(row, 1)
                model_name = model_item.data(Qt.UserRole) or model_item.text()
                
                # 从显示文本中提取原始模型名称（如果没有存储在UserRole中）
                if not model_name and "(" in model_item.text():
                    model_name = model_item.text().split(" (")[0]
                
                index = -1
                
                if api_type == "gemini":
                    for i, api in enumerate(GEMINI_API_CONFIG):
                        if api.get("model", "未指定") == model_name:
                            index = i
                            break
                elif api_type == "openai":
                    for i, api in enumerate(OPENAI_API_CONFIG):
                        if api.get("model", "未指定") == model_name:
                            index = i
                            break
                
                if index >= 0:
                    self.test_api(api_type, index)
        
        # 启用测试按钮
        self.test_all_button.setEnabled(True)
        self.test_all_button.setText("测试全部API")
    
    def test_api(self, api_type, index):
        """测试指定的API"""
        # 获取API信息
        api_key = ""
        api_model = ""
        api_id = f"{api_type}_{index}"
        
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
        for row in range(self.api_table.rowCount()):
            api_type_text = self.api_table.item(row, 0).text()
            api_model_text = self.api_table.item(row, 1).text()
            
            if ((api_type == "gemini" and api_type_text == "Gemini") or 
                (api_type == "openai" and api_type_text == "OpenAI")) and api_model_text == api_model:
                self.api_table.item(row, 2).setText("测试中...")
                # 禁用测试按钮
                if self.api_table.cellWidget(row, 3):
                    self.api_table.cellWidget(row, 3).setEnabled(False)
                break
        
        # 在后台线程中测试API连接
        thread = threading.Thread(target=self._test_api_connection, 
                                args=(api_id, api_type, api_key, api_model))
        thread.daemon = True
        thread.start()
    
    def _test_api_connection(self, api_id, api_type, api_key, model):
        """在后台线程中测试API连接，参考api_service.py的实现"""
        try:
            if api_type == "gemini":
                # 测试Gemini API
                # 获取更多参数
                api_index = int(api_id.split('_')[1])
                api_config = GEMINI_API_CONFIG[api_index]
                redirect_url = api_config.get('redirect_url', '')
                
                # 构建正确的API URL格式
                # 不同API服务商可能有不同的URL格式
                final_api_url = ""
                
                # 针对官方Google API的正规URL格式
                if redirect_url and "generativelanguage.googleapis.com" in redirect_url:
                    # 官方格式: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_API_KEY
                    if ":generateContent" in redirect_url:
                        # 完整URL已提供
                        final_api_url = redirect_url
                    else:
                        # 只提供了基础URL，需要添加模型和方法
                        if redirect_url.endswith('/'):
                            final_api_url = f"{redirect_url}{model}:generateContent"
                        else:
                            final_api_url = f"{redirect_url}/{model}:generateContent"
                    
                    # 添加API密钥参数
                    if "key=" not in final_api_url:
                        if "?" in final_api_url:
                            final_api_url += f"&key={api_key}"
                        else:
                            final_api_url += f"?key={api_key}"
                
                # 针对第三方API服务商的URL格式
                elif redirect_url:
                    if ":generateContent" in redirect_url:
                        final_api_url = redirect_url
                    else:
                        if redirect_url.endswith('/'):
                            final_api_url = f"{redirect_url}{model}:generateContent"
                        else:
                            final_api_url = f"{redirect_url}/{model}:generateContent"
                else:
                    # 使用默认URL格式 
                    final_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    
                    # 添加API密钥
                    if "key=" not in final_api_url:
                        final_api_url += f"?key={api_key}"
                
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
                
                # 构建请求头
                headers = {
                    "Content-Type": "application/json"
                }
                
                # 为不同API服务商设置不同的请求头
                if redirect_url and "aliyahzombie" in redirect_url:
                    # 使用自定义标头
                    headers["x-goog-api-key"] = api_key
                elif "key=" not in final_api_url:
                    # 如果URL中没有key参数，则在请求头中添加
                    headers["x-goog-api-key"] = api_key
                
                # 打印请求信息，帮助诊断
                print(f"请求URL: {final_api_url}")
                print(f"请求头: {headers}")
                print(f"请求体示例: {json.dumps(request_data, ensure_ascii=False)[:100]}...")
                
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
            
            elif api_type == "openai":
                # 测试OpenAI API
                # 获取更多参数
                api_index = int(api_id.split('_')[1])
                api_config = OPENAI_API_CONFIG[api_index]
                redirect_url = api_config.get('redirect_url', '')
                
                # 构建正确的API URL格式 - 避免添加额外的路径
                if redirect_url:
                    # 使用提供的redirect_url作为完整URL
                    final_api_url = redirect_url.strip()
                    print(f"原始redirect_url: {redirect_url}")
                    
                    # 确保我们不重复添加路径部分
                    if final_api_url.endswith('/'):
                        final_api_url = final_api_url.rstrip('/')
                    
                    # 使用正则表达式判断URL是否已经包含API路径
                    has_api_path = re.search(r'/(api|v1)/.*?(chat/completions|/chat/completions)$', final_api_url) is not None
                    
                    # 第三方API的URL处理逻辑（不再限于hf.space）
                    if "openai.com" in final_api_url:
                        # 对于官方OpenAI API，使用标准格式
                        if not has_api_path and not final_api_url.endswith('/v1'):
                            # 确保使用正确的官方路径
                            final_api_url = final_api_url.rstrip('/')
                            if not final_api_url.endswith('/v1'):
                                final_api_url += "/v1"
                            final_api_url += "/chat/completions"
                    elif has_api_path:
                        # 如果URL已包含API路径(如/api/v1/chat/completions)，不做修改
                        print("URL已包含完整API路径，不做修改")
                    else:
                        # 对于所有其他第三方API，尝试常见的路径格式
                        print(f"第三方API URL: {final_api_url}")
                        
                        # 对于所有第三方API（包括但不限于hf.space）
                        # 移除URL末尾可能的斜杠
                        base_url = final_api_url.rstrip('/')
                        
                        # 检查是否有子路径需要保留
                        if "/api" in final_api_url and not final_api_url.endswith("/api"):
                            # 如果URL已包含/api但不是以/api结尾，检查是否需要添加剩余部分
                            if not re.search(r'/api/.*?/chat/completions$', final_api_url):
                                if re.search(r'/api/v1/?$', final_api_url):
                                    # 如果URL以/api/v1结尾，添加/chat/completions
                                    final_api_url += "/chat/completions"
                                elif re.search(r'/api/?$', final_api_url):
                                    # 如果URL以/api结尾，添加/v1/chat/completions
                                    final_api_url += "/v1/chat/completions"
                            print(f"调整后的URL: {final_api_url}")
                        else:
                            # 尝试所有可能的路径组合
                            possible_paths = [
                                "/api/v1/chat/completions",  # 最常见的格式
                                "/v1/chat/completions",      # OpenAI兼容格式
                                "/chat/completions",         # 简化格式
                                "/api/chat/completions"      # 另一种常见格式
                            ]
                            
                            print(f"测试多种API路径组合...")
                            found_working_url = False
                            
                            # 先尝试使用预检请求(OPTIONS)检查路径是否有效
                            for path in possible_paths:
                                test_url = f"{base_url}{path}"
                                print(f"尝试API路径: {test_url}")
                                
                                try:
                                    # 使用OPTIONS请求预检
                                    options_headers = {
                                        "Origin": base_url,
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                                    }
                                    
                                    options_response = requests.options(
                                        test_url, 
                                        timeout=5,
                                        headers=options_headers
                                    )
                                    
                                    # 检查是否接受POST方法
                                    allow_header = options_response.headers.get('Allow', '')
                                    if 'POST' in allow_header or options_response.status_code < 400:
                                        print(f"找到有效API路径: {test_url}")
                                        final_api_url = test_url
                                        found_working_url = True
                                        break
                                    else:
                                        print(f"路径响应 {options_response.status_code}，但不允许POST")
                                except Exception as e:
                                    print(f"测试路径失败: {str(e)}")
                            
                            # 如果没找到有效路径，使用最常见的格式
                            if not found_working_url:
                                print("未找到有效API路径，使用默认路径")
                                # 根据URL是否包含某些关键词选择不同的默认路径
                                if "openai" in base_url.lower():
                                    # OpenAI风格API
                                    final_api_url = f"{base_url}/v1/chat/completions"
                                else:
                                    # 一般第三方API
                                    final_api_url = f"{base_url}/api/v1/chat/completions"
                                
                            print(f"最终确定的URL: {final_api_url}")
                else:
                    # 使用官方OpenAI端点
                    final_api_url = "https://api.openai.com/v1/chat/completions"
                
                print(f"最终OpenAI API测试URL: {final_api_url}")
                
                # 构建OpenAI格式的请求体
                request_data = {
                    "model": model,
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
                
                # 针对所有第三方API添加浏览器模拟头
                if redirect_url and not "openai.com" in redirect_url:
                    print("添加第三方API特殊请求头")
                    # 通用的浏览器模拟头
                    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                    
                    # 处理Origin和Referer
                    try:
                        # 获取域名部分作为Origin
                        from urllib.parse import urlparse
                        parsed_url = urlparse(final_api_url)
                        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        headers["Origin"] = origin
                        headers["Referer"] = origin + "/"
                        print(f"设置Origin: {origin}, Referer: {origin}/")
                        
                        # 添加额外的浏览器头部，对所有第三方API可能都有用
                        headers["Accept"] = "application/json, text/plain, */*"
                        headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
                        headers["sec-ch-ua"] = '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"'
                        headers["sec-ch-ua-mobile"] = "?0"
                        headers["sec-ch-ua-platform"] = '"Windows"'
                        headers["Sec-Fetch-Dest"] = "empty"
                        headers["Sec-Fetch-Mode"] = "cors"
                        headers["Sec-Fetch-Site"] = "same-origin"
                        
                    except Exception as e:
                        print(f"解析URL失败: {str(e)}")
                    
                # 打印请求信息，帮助诊断
                print(f"请求URL: {final_api_url}")
                print(f"请求头: {headers}")
                print(f"请求体: {json.dumps(request_data, ensure_ascii=False)}")
                
                # 发送请求
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
                    status_code = e.response.status_code if hasattr(e, 'response') else None
                    
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
                        if hasattr(e, 'response'):
                            error_msg = f"{error_msg} - 响应: {e.response.text[:100]}"
                    
                    # 特殊处理hf.space的错误
                    if "hf.space" in final_api_url and status_code == 404:
                        print("HF Space API返回404，尝试其他URL格式")
                        
                        # 如果返回404，可能是路径格式问题，尝试直接访问域名
                        from urllib.parse import urlparse
                        parsed_url = urlparse(final_api_url)
                        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        
                        # 尝试其他API路径格式
                        alternate_paths = [
                            "/api/v1/chat/completions",
                            "/v1/chat/completions",
                            "/chat/completions"
                        ]
                        
                        for alt_path in alternate_paths:
                            alt_url = f"{base_domain}{alt_path}"
                            if alt_url != final_api_url:  # 避免重复尝试相同URL
                                print(f"尝试替代URL: {alt_url}")
                                
                                try:
                                    alt_response = requests.post(
                                        alt_url, 
                                        headers=headers,
                                        json=request_data,
                                        timeout=15
                                    )
                                    
                                    if alt_response.status_code < 400:
                                        print(f"替代URL请求成功: {alt_url}")
                                        # 处理成功响应
                                        alt_json = alt_response.json()
                                        if "choices" in alt_json and len(alt_json["choices"]) > 0:
                                            self.signals.test_complete.emit(api_id, True, "")
                                            return
                                except Exception as alt_err:
                                    print(f"替代URL请求失败: {str(alt_err)}")
                        
                        # 如果所有替代URL都失败，记录详细错误
                        error_msg = f"API连接失败: 所有可能的URL格式都返回错误。原始错误: {error_msg}"
                    
                    # 对所有第三方API（非官方OpenAI）进行通用错误处理
                    elif redirect_url and "openai.com" not in redirect_url and status_code == 404:
                        print("第三方API返回404，尝试其他常见URL格式")
                        
                        # 解析URL，获取基础域名
                        from urllib.parse import urlparse
                        parsed_url = urlparse(final_api_url)
                        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        
                        # 尝试各种常见的API路径格式
                        alternate_paths = [
                            "/api/v1/chat/completions",
                            "/v1/chat/completions",
                            "/chat/completions",
                            "/api/chat/completions",
                            # 一些特定路径格式
                            "/v1/engines/"+model+"/completions",  # 旧版OpenAI格式
                            "/openai/deployments/"+model+"/chat/completions",  # Azure风格
                            "/api/openai/v1/chat/completions"  # 某些代理服务使用
                        ]
                        
                        # 根据URL特征添加可能的路径
                        if "azure" in base_domain:
                            alternate_paths.append("/openai/deployments/"+model+"/chat/completions?api-version=2023-05-15")
                        
                        success = False
                        for alt_path in alternate_paths:
                            alt_url = f"{base_domain}{alt_path}"
                            if alt_url != final_api_url:  # 避免重复尝试相同URL
                                print(f"尝试替代URL: {alt_url}")
                                
                                try:
                                    # 添加请求参数后的短超时
                                    alt_response = requests.post(
                                        alt_url, 
                                        headers=headers,
                                        json=request_data,
                                        timeout=15
                                    )
                                    
                                    if alt_response.status_code < 400:
                                        print(f"替代URL请求成功: {alt_url}")
                                        # 处理成功响应
                                        try:
                                            alt_json = alt_response.json()
                                            if ("choices" in alt_json and len(alt_json["choices"]) > 0) or \
                                               ("response" in alt_json) or \
                                               ("output" in alt_json):
                                                success = True
                                                self.signals.test_complete.emit(api_id, True, "")
                                                return
                                        except:
                                            print("响应不是有效的JSON")
                                except Exception as alt_err:
                                    print(f"替代URL请求失败: {str(alt_err)}")
                        
                        if not success:
                            # 记录详细错误信息
                            error_msg = f"API连接失败: 尝试了多种URL格式但均失败。原始错误: {error_msg}"
                    
                    self.signals.test_complete.emit(api_id, False, f"HTTP错误 {status_code}: {error_msg}")
                    return
            
            else:
                self.signals.test_complete.emit(api_id, False, f"不支持的API类型: {api_type}")
        
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            status_code = e.response.status_code if hasattr(e, 'response') else None
            
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
                if hasattr(e, 'response'):
                    error_msg = f"{error_msg} - 响应: {e.response.text[:100]}"
                    
            self.signals.test_complete.emit(api_id, False, f"HTTP错误 {status_code}: {error_msg}")
            
        except requests.exceptions.ConnectionError:
            self.signals.test_complete.emit(api_id, False, "连接错误，请检查网络或API端点是否正确")
            
        except requests.exceptions.Timeout:
            self.signals.test_complete.emit(api_id, False, "请求超时，API服务器可能响应较慢")
            
        except requests.exceptions.RequestException as e:
            self.signals.test_complete.emit(api_id, False, f"请求错误: {str(e)}")
            
        except json.JSONDecodeError:
            self.signals.test_complete.emit(api_id, False, "无法解析API响应，返回的不是有效的JSON")
            
        except Exception as e:
            import traceback
            print(f"未捕获异常: {str(e)}")
            print(traceback.format_exc())
            self.signals.test_complete.emit(api_id, False, f"测试出错: {str(e)}")
    
    def on_test_complete(self, api_id, success, error_message):
        """测试完成后的回调"""
        # 解析API ID
        parts = api_id.split("_")
        if len(parts) != 2:
            return
        
        api_type = parts[0]
        index = int(parts[1])
        
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
        for row in range(self.api_table.rowCount()):
            api_type_text = self.api_table.item(row, 0).text()
            model_item = self.api_table.item(row, 1)
            
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
                break 