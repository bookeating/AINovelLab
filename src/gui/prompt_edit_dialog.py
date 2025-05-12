# -*- coding: utf-8 -*-
"""小说处理工具的提示词编辑对话框"""

import os
import sys
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QMessageBox, QTextEdit, QSpinBox, QGroupBox, 
                           QComboBox, QDialog, QDialogButtonBox, QSplitter)
from PyQt5.QtCore import pyqtSignal, Qt

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入配置模块
try:
    from core.novel_condenser import config
    from core.novel_condenser.config import save_config_to_file
except ImportError:
    from src.core.novel_condenser import config
    try:
        from src.core.novel_condenser.config import save_config_to_file
    except ImportError:
        save_config_to_file = None

from .worker import WorkerThread

class PromptEditDialog(QDialog):
    """提示词编辑和测试对话框"""
    
    # 类常量
    DEFAULT_PROMPT = '你是一位专业的小说内容整理与改写专家。你的任务是将下面的小说内容（原文 {original_count}字）调整为一个更简洁的版本。调整后版本的字数应在 {min_count} 字到 {max_count} 字之间，请务必严格控制产出字数在该范围内。\n\n请严格遵循以下要求：\n\n主线完整：完整保留故事的主线情节与所有关键转折点。不允许遗漏任何重要剧情推进环节。\n人物塑造：保留主要人物性格、形象发展至关重要的对话、内心活动和互动细节。\n环境氛围：保留对理解世界观、故事背景、气氛营造有核心作用的环境描写与关键细节（但避免无关冗余描写）。\n重要配角与线索：不遗漏任何对情节发展有显著影响的次要人物和叙事线索。\n风格连贯流畅：确保压缩后的文本连贯、流畅，逻辑清楚，尽量保持原作风格和叙事调性。\n动态回补机制：初步整理完成后，请统计自己整理后文本的字数。如果字数低于目标下限 {min_count}，请回溯补充之前可能略去的次要情节、气氛描写、对主配角的心理刻画、对话或有助主旨细节，直至内容字数达到要求。\n禁止输出范围外字数：不允许输出低于 {min_count}或高于 {max_count} 字的文本。\n\n输出格式与注意事项：\n直接输出脱水压缩后的文本本身，不要添加任何前言、说明、评论、总结、序号或标题。\n如果整理后确实已到目标范围上限，但仍有部分细节未能保留，在不影响主线流畅的前提下可以适当取舍，但必须优先保障上述 1-5 点。'
    MAX_FILES = 50  # 限制最多显示的文件数量
    
    def __init__(self, txt_files, parent=None):
        """初始化提示词编辑对话框"""
        super().__init__(parent)
        self.txt_files = txt_files[:self.MAX_FILES] if txt_files and len(txt_files) > self.MAX_FILES else (txt_files or [])
        self.prompt_changed = False
        self.original_prompt = config.PROMPT_TEMPLATES.get("novel_condenser", "")
        self.current_prompt = self.original_prompt
        self.successful_keys = set()  # 记录成功测试的密钥
        
        self.setWindowTitle("提示词调整")
        self.resize(800, 600)
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建提示词编辑区
        prompt_layout = QVBoxLayout()
        header = QHBoxLayout()
        header.addWidget(QLabel("提示词模板:"))
        header.addStretch()
        
        reset_btn = QPushButton("重置")
        reset_btn.setToolTip("重置为默认提示词")
        reset_btn.clicked.connect(self.reset_prompt)
        header.addWidget(reset_btn)
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setText(self.current_prompt)
        self.prompt_edit.setMinimumHeight(100)
        
        prompt_layout.addLayout(header)
        prompt_layout.addWidget(self.prompt_edit)
        layout.addLayout(prompt_layout)
        
        # 变量信息区
        var_info = QLabel("提示词模板中可用变量: {original_count}=原文字数, {min_count}=最小目标字数, {max_count}=最大目标字数")
        var_info.setStyleSheet("color: #555555; font-style: italic; padding-left: 5px;")
        var_info.setWordWrap(True)
        layout.addWidget(var_info)
        
        # 章节选择区（如果有文件）
        if self.txt_files:
            chapter_layout = QHBoxLayout()
            chapter_layout.addWidget(QLabel("选择测试章节:"))
            
            self.chapter_combo = QComboBox()
            self.populate_chapter_combo()
            self.chapter_combo.currentIndexChanged.connect(self.load_selected_chapter)
            chapter_layout.addWidget(self.chapter_combo)
            chapter_layout.addStretch()
            layout.addLayout(chapter_layout)
        
        # API测试区
        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("选择API密钥:"))
        self.key_combo = QComboBox()
        self.populate_key_combo()
        test_layout.addWidget(self.key_combo)
        test_layout.addSpacing(15)
        
        # 压缩比例设置
        ratio_layout = QVBoxLayout()
        ratio_control = QHBoxLayout()
        ratio_control.addWidget(QLabel("测试压缩比:"))
        
        self.test_min_ratio_spin = QSpinBox()
        self.test_min_ratio_spin.setRange(1, 99)
        self.test_min_ratio_spin.setValue(config.MIN_CONDENSATION_RATIO)
        self.test_min_ratio_spin.setSuffix("%")
        self.test_min_ratio_spin.valueChanged.connect(self.update_target_count_display)
        
        self.test_max_ratio_spin = QSpinBox()
        self.test_max_ratio_spin.setRange(1, 99)
        self.test_max_ratio_spin.setValue(config.MAX_CONDENSATION_RATIO)
        self.test_max_ratio_spin.setSuffix("%")
        self.test_max_ratio_spin.valueChanged.connect(self.update_target_count_display)
        
        ratio_control.addWidget(self.test_min_ratio_spin)
        ratio_control.addWidget(QLabel("-"))
        ratio_control.addWidget(self.test_max_ratio_spin)
        ratio_control.addStretch(1)
        
        ratio_layout.addLayout(ratio_control)
        
        self.target_count_label = QLabel("目标字数范围: （请先输入原文）")
        self.target_count_label.setStyleSheet("color: #555555; font-style: italic;")
        ratio_layout.addWidget(self.target_count_label)
        
        test_layout.addLayout(ratio_layout)
        
        self.test_button = QPushButton("单次脱水测试")
        self.test_button.clicked.connect(self.test_condense)
        test_layout.addWidget(self.test_button)
        
        # 如果没有API密钥，禁用测试按钮
        if self.key_combo.count() == 0 or self.key_combo.itemData(0) is None:
            self.test_button.setEnabled(False)
        
        layout.addLayout(test_layout)
        
        # 内容显示区
        splitter = QSplitter(Qt.Horizontal)
        
        # 原始内容区
        original_group = QGroupBox("原始内容 (可编辑)")
        original_layout = QVBoxLayout()
        self.original_text = QTextEdit()
        self.original_text.setPlaceholderText("在此输入或粘贴待脱水的原始文本...")
        self.original_text.textChanged.connect(self.update_target_count_display)
        original_layout.addWidget(self.original_text)
        original_group.setLayout(original_layout)
        
        # 脱水结果区
        condensed_group = QGroupBox("脱水结果")
        condensed_layout = QVBoxLayout()
        self.condensed_text = QTextEdit()
        self.condensed_text.setReadOnly(True)
        condensed_layout.addWidget(self.condensed_text)
        condensed_group.setLayout(condensed_layout)
        
        splitter.addWidget(original_group)
        splitter.addWidget(condensed_group)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter, 1)
        
        # 状态和按钮
        self.status_label = QLabel("就绪")
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_prompt)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(self.status_label)
        layout.addWidget(button_box)
        
        # 初始更新字数显示
        self.update_target_count_display()
    
    def set_ui_enabled(self, enabled=True):
        """统一设置UI控件的启用状态"""
        self.test_button.setEnabled(enabled)
        self.prompt_edit.setEnabled(enabled)
        self.original_text.setEnabled(enabled)
        self.key_combo.setEnabled(enabled and (self.key_combo.count() > 0 and self.key_combo.itemData(0) is not None))
        self.test_min_ratio_spin.setEnabled(enabled)
        self.test_max_ratio_spin.setEnabled(enabled)
    
    def populate_chapter_combo(self):
        """填充章节下拉框"""
        if not self.txt_files:
            return
        
        self.chapter_combo.setUpdatesEnabled(False)
        self.chapter_combo.clear()
        try:
            for i, file_path in enumerate(self.txt_files):
                self.chapter_combo.addItem(f"{i+1}. {os.path.basename(file_path)}", file_path)
        finally:
            self.chapter_combo.setUpdatesEnabled(True)
    
    def populate_key_combo(self):
        """填充API密钥下拉框"""
        self.key_combo.clear()
        api_keys = []
        
        # 添加Gemini API密钥
        if hasattr(config, 'GEMINI_API_CONFIG') and config.GEMINI_API_CONFIG:
            for i, _ in enumerate(config.GEMINI_API_CONFIG):
                key_id = f"gemini_{i+1}"
                display_name = f"Gemini #{i+1}" + (" ✓" if key_id in self.successful_keys else "")
                api_keys.append((display_name, {"type": "gemini", "index": i}))
        
        # 添加OpenAI API密钥
        if hasattr(config, 'OPENAI_API_CONFIG') and config.OPENAI_API_CONFIG:
            for i, _ in enumerate(config.OPENAI_API_CONFIG):
                key_id = f"openai_{i+1}"
                display_name = f"OpenAI #{i+1}" + (" ✓" if key_id in self.successful_keys else "")
                api_keys.append((display_name, {"type": "openai", "index": i}))
        
        # 填充下拉框
        if api_keys:
            for display_name, key_data in api_keys:
                self.key_combo.addItem(display_name, key_data)
            self.key_combo.setEnabled(True)
        else:
            self.key_combo.addItem("无可用API密钥", None)
            self.key_combo.setEnabled(False)
            self.test_button.setEnabled(False)
    
    def load_chapter_content(self, file_path=None):
        """加载章节内容"""
        if file_path is None:
            current_index = self.chapter_combo.currentIndex()
            if current_index < 0 or current_index >= len(self.txt_files):
                return ""
            file_path = self.txt_files[current_index]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取章节内容: {str(e)}")
            return ""
    
    def load_selected_chapter(self):
        """当章节选择改变时加载内容"""
        content = self.load_chapter_content()
        if content:
            self.original_text.setText(content)
    
    def reset_prompt(self):
        """重置提示词为默认值"""
        self.prompt_edit.setText(self.DEFAULT_PROMPT)
        QMessageBox.information(self, "提示", "提示词已重置为默认值")
    
    def test_condense(self):
        """使用当前提示词进行单次脱水测试"""
        # 检查输入和配置
        content = self.original_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "错误", "请先输入或选择原始内容")
            return
        
        custom_prompt = self.prompt_edit.toPlainText().strip()
        if not custom_prompt:
            QMessageBox.warning(self, "错误", "提示词不能为空")
            return
        
        key_data = self.key_combo.currentData()
        if key_data is None:
            QMessageBox.warning(self, "错误", "无可用API密钥，请先在主程序配置API密钥")
            return

        # 压缩比例检查
        test_min_ratio = self.test_min_ratio_spin.value()
        test_max_ratio = self.test_max_ratio_spin.value()
        if test_min_ratio >= test_max_ratio:
            QMessageBox.warning(self, "错误", "最小压缩比例必须小于最大压缩比例")
            return
            
        # 变量检查
        missing_vars = [var for var in ["{original_count}", "{min_count}", "{max_count}"] 
                        if var not in custom_prompt]
        if missing_vars and QMessageBox.warning(
            self, "提示词变量检查", 
            f"提示词中缺少必要的变量: {', '.join(missing_vars)}。\n"
            "这可能导致脱水结果与输入内容无关。是否继续？",
            QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        
        # 开始处理
        self.status_label.setText("正在处理中...")
        self.set_ui_enabled(False)
        self.condensed_text.clear()
        
        # 创建处理线程
        self.worker_thread = CondensingTestThread(content, custom_prompt, key_data, test_min_ratio, test_max_ratio)
        self.worker_thread.result_ready.connect(self.on_test_complete)
        self.worker_thread.error_occurred.connect(self.on_test_error)
        self.worker_thread.start()
    
    def on_test_complete(self, result_data):
        """测试完成时的回调函数"""
        # 提取结果数据
        condensed_content = result_data.get("content", "")
        key_info = result_data.get("key_info", {})
        debug_info = result_data.get("debug_info", {})
        self.last_result_data = result_data
        
        # 更新结果显示
        self.condensed_text.setText(condensed_content)
        
        # 计算字数统计
        original_chars = len(self.original_text.toPlainText())
        condensed_chars = len(condensed_content)
        ratio = round((condensed_chars / original_chars) * 100, 2) if original_chars > 0 else 0
        
        # 目标字数范围
        min_ratio = self.test_min_ratio_spin.value()
        max_ratio = self.test_max_ratio_spin.value()
        target_min = int(original_chars * min_ratio / 100)
        target_max = int(original_chars * max_ratio / 100)
        
        # 构建状态信息
        status_parts = [
            "测试完成",
            f"原文: {original_chars}字",
            f"结果: {condensed_chars}字",
            f"比例: {ratio}%", 
            f"目标范围: {target_min}-{target_max}字"
        ]
        
        # 记录使用的API
        if key_info.get("type") and key_info.get("index") is not None:
            key_type = key_info["type"]
            key_index = key_info["index"]
            key_id = f"{key_type}_{key_index+1}"
            self.successful_keys.add(key_id)
            status_parts.append(f"使用: {key_type.capitalize()} #{key_index+1}")
            self.populate_key_combo()
            
        # 更新状态显示
        self.status_label.setText(" | ".join(status_parts))
        
        # 检查异常比例
        if original_chars > 0 and condensed_chars > 0 and (ratio < 5 or ratio > 200):
            QMessageBox.warning(
                self, "API响应异常", 
                f"脱水结果比例({ratio}%)异常，可能与输入内容无关。\n\n"
                f"请检查提示词模板是否正确，或尝试使用不同的API密钥。\n\n"
                f"原文长度: {original_chars}字\n"
                f"结果长度: {condensed_chars}字\n"
                f"目标范围: {target_min}-{target_max}字"
            )
            
            print("[调试] 当前使用的提示词模板:")
            print(self.prompt_edit.toPlainText())
            
            if "error" in debug_info:
                print(f"[调试] 发生错误: {debug_info['error']}")
        
        # 恢复UI状态
        self.set_ui_enabled(True)
    
    def on_test_error(self, error_message):
        """测试出错时的回调函数"""
        QMessageBox.critical(self, "测试失败", f"脱水测试失败: {error_message}")
        self.status_label.setText(f"测试失败: {error_message}")
        self.set_ui_enabled(True)
    
    def save_prompt(self):
        """保存提示词到配置"""
        custom_prompt = self.prompt_edit.toPlainText().strip()
        
        # 如果没有变化，直接关闭
        if custom_prompt == self.original_prompt:
            self.accept()
            return
        
        # 更新全局提示词
        config.PROMPT_TEMPLATES["novel_condenser"] = custom_prompt
        self.prompt_changed = True
        self.current_prompt = custom_prompt
        
        # 保存到配置文件
        try:
            if save_config_to_file:
                success = save_config_to_file(custom_prompt)
                self.show_save_result(success)
            else:
                self.show_save_result(False)
        except ImportError:
            self.show_save_result(False)
        
        self.accept()
    
    def show_save_result(self, success):
        """显示保存结果消息"""
        title, msg = (
            ("保存成功", "提示词已更新并保存到配置文件，将用于后续的脱水处理") if success else
            ("保存警告", "提示词已更新但保存到配置文件失败，仅在本次会话中有效")
        )
        (QMessageBox.information if success else QMessageBox.warning)(self, title, msg)

    def update_target_count_display(self):
        """更新目标字数范围显示"""
        original_count = len(self.original_text.toPlainText())
        
        if original_count > 0:
            min_ratio = self.test_min_ratio_spin.value()
            max_ratio = self.test_max_ratio_spin.value()
            min_count = int(original_count * min_ratio / 100)
            max_count = int(original_count * max_ratio / 100)
            self.target_count_label.setText(f"目标字数范围: {min_count} - {max_count}字 (原文{original_count}字)")
        else:
            self.target_count_label.setText("目标字数范围: （请先输入原文）")

    def prompt_preview(self):
        """返回当前提示词的预览"""
        prompt = self.current_prompt
        return prompt[:100] + "..." if len(prompt) > 100 else prompt


class CondensingTestThread(WorkerThread):
    """脱水测试线程，用于异步处理内容压缩测试"""
    
    result_ready = pyqtSignal(dict)  # 测试结果信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, content, custom_prompt, key_data, test_min_ratio, test_max_ratio):
        """初始化脱水测试线程"""
        super().__init__("test_condense", {
            "content": content, 
            "custom_prompt": custom_prompt, 
            "key_data": key_data,
            "test_min_ratio": test_min_ratio,
            "test_max_ratio": test_max_ratio
        })
        
    def run(self):
        """执行线程"""
        # 保存原始配置
        original_settings = {
            "min_ratio": config.MIN_CONDENSATION_RATIO,
            "max_ratio": config.MAX_CONDENSATION_RATIO,
            "prompt": config.PROMPT_TEMPLATES.get("novel_condenser", "")
        }
        
        try:
            # 应用测试配置
            config.PROMPT_TEMPLATES["novel_condenser"] = self.args.get("custom_prompt", "")
            config.MIN_CONDENSATION_RATIO = self.args.get("test_min_ratio")
            config.MAX_CONDENSATION_RATIO = self.args.get("test_max_ratio")
            
            # 执行API调用
            result_data = self.call_api()
            
            # 处理结果
            if result_data["content"]:
                self.result_ready.emit(result_data)
            else:
                key_data = self.args.get("key_data", {})
                key_type = key_data.get("type", "未知")
                key_index = key_data.get("index", 0)
                self.error_occurred.emit(f"使用 {key_type.capitalize()} #{key_index+1} 进行API脱水处理失败")
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
        finally:
            # 恢复原始配置
            config.PROMPT_TEMPLATES["novel_condenser"] = original_settings["prompt"]
            config.MIN_CONDENSATION_RATIO = original_settings["min_ratio"]
            config.MAX_CONDENSATION_RATIO = original_settings["max_ratio"]
    
    def call_api(self):
        """调用API进行内容处理"""
        content = self.args.get("content", "")
        key_data = self.args.get("key_data", {})
        key_type = key_data.get("type")
        key_index = key_data.get("index")
        custom_prompt = self.args.get("custom_prompt", "")
        
        # 打印调试信息
        print(f"[调试] 准备调用API，内容长度：{len(content)}字")
        print(f"[调试] 目标压缩比例：{config.MIN_CONDENSATION_RATIO}%-{config.MAX_CONDENSATION_RATIO}%")
        
        # 初始化结果数据
        result_data = {
            "content": "", 
            "key_info": {}, 
            "debug_info": {
                "content_length": len(content),
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "prompt_template": custom_prompt,
                "min_ratio": config.MIN_CONDENSATION_RATIO,
                "max_ratio": config.MAX_CONDENSATION_RATIO,
                "api_type": key_type,
            }
        }
        
        # 导入API模块
        try:
            from src.core.novel_condenser.api_service import (
                condense_novel_gemini, condense_novel_openai, generate_novel_condenser_prompt
            )
        except ImportError:
            try:
                from core.novel_condenser.api_service import (
                    condense_novel_gemini, condense_novel_openai, generate_novel_condenser_prompt
                )
            except ImportError as e:
                print(f"[调试] 导入API服务模块失败: {e}")
                return result_data
        
        # 调用相应API
        api_caller = None
        if key_type == "gemini" and hasattr(config, 'GEMINI_API_CONFIG') and key_index < len(config.GEMINI_API_CONFIG):
            api_caller = lambda: condense_novel_gemini(
                content, 
                api_key_config=config.GEMINI_API_CONFIG[key_index],
                custom_prompt_template=custom_prompt
            )
        elif key_type == "openai" and hasattr(config, 'OPENAI_API_CONFIG') and key_index < len(config.OPENAI_API_CONFIG):
            api_caller = lambda: condense_novel_openai(
                content, 
                api_key_config=config.OPENAI_API_CONFIG[key_index],
                custom_prompt_template=custom_prompt
            )
        
        # 执行API调用
        if api_caller:
            try:
                # 记录实际使用的提示词
                calc_prompt = generate_novel_condenser_prompt(
                    content_length=len(content),
                    custom_prompt_template=custom_prompt
                )
                print(f"[调试] 计算的提示词: {calc_prompt}")
                
                # 调用API
                condensed = api_caller()
                if condensed:
                    result_data["content"] = condensed
                    result_data["key_info"] = {"type": key_type, "index": key_index}
                    print(f"[调试] API调用成功，返回内容长度：{len(condensed)}字")
                else:
                    print(f"[调试] API调用返回空内容")
            except Exception as e:
                import traceback
                error_stack = traceback.format_exc()
                print(f"[调试] API调用异常：{str(e)}\n{error_stack}")
                result_data["debug_info"]["error"] = f"{str(e)}\n{error_stack}"
        else:
            print(f"[调试] 无法获取API处理函数或密钥索引无效: type={key_type}, index={key_index}")
        
        return result_data 