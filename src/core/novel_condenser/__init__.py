#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说脱水工具包 - 使用LLM将小说内容缩短至30%-50%

本工具支持通过Gemini API对小说内容进行压缩处理。
支持单文件处理和批量处理，支持多API密钥并发处理，
可以识别目录类型文件并自动处理。
"""

__version__ = "1.0.0"

# 导入主要组件，方便外部直接使用
from .main import main
from .api_service import condense_novel_gemini
from .file_utils import save_condensed_novel, is_directory_file 