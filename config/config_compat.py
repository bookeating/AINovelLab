#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置兼容层 - 确保配置正确导入
"""

import os
import sys

def ensure_config_importable():
    """确保能够从任何路径导入配置模块"""
    # 当前文件所在目录
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取项目根目录
    project_root = os.path.dirname(current_file_dir)
    
    # 添加项目根目录和配置目录到导入路径
    paths_to_add = [
        project_root,    # 项目根目录
        current_file_dir  # 配置目录
    ]
    
    # 将路径添加到sys.path
    for path in paths_to_add:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    
    return True

# 在导入时自动执行
ensure_config_importable() 