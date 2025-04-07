#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
核心模块导入辅助 - 确保能够正确导入所有依赖
"""

import os
import sys

def setup_imports():
    """设置正确的导入路径"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 计算项目目录结构
    core_dir = current_dir
    src_dir = os.path.dirname(core_dir)
    project_root = os.path.dirname(src_dir)
    
    # 添加配置目录路径
    config_dir = os.path.join(project_root, "config")
    
    # 使用项目根目录的api_keys.json文件
    api_keys_path = os.path.join(project_root, "api_keys.json")
    
    # 添加所有可能的路径
    paths_to_add = [
        core_dir,      # core目录
        src_dir,       # src目录
        project_root,  # 项目根目录
        config_dir,    # 配置目录
    ]
    
    # 将路径添加到sys.path
    for path in paths_to_add:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    
    # 返回路径信息，以便使用
    return {
        "core_dir": core_dir,
        "src_dir": src_dir,
        "project_root": project_root,
        "config_dir": config_dir,
        "api_keys_path": api_keys_path
    }

# 在导入时自动执行
paths = setup_imports() 