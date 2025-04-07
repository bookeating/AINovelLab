#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI辅助模块 - 提供导入和路径管理工具
"""

import os
import sys

def ensure_imports():
    """确保能够正确导入核心模块，无论在哪种项目结构下"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 计算项目目录结构
    gui_dir = current_dir
    src_dir = os.path.dirname(gui_dir)
    project_root = os.path.dirname(src_dir)
    
    # 添加所有可能的路径
    paths_to_add = [
        gui_dir,     # GUI目录
        src_dir,     # src目录
        project_root, # 项目根目录
    ]
    
    # 将路径添加到sys.path
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # 返回路径信息，以便使用
    return {
        "gui_dir": gui_dir,
        "src_dir": src_dir,
        "project_root": project_root
    }

# 在导入时自动执行
paths = ensure_imports() 