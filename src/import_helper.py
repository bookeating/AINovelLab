#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入辅助模块 - 解决模块导入路径问题
"""

import os
import sys
import traceback

def setup_paths():
    """设置所有可能的导入路径"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 计算项目目录结构
    src_dir = current_dir
    project_root = os.path.dirname(src_dir)
    
    # 获取所有需要添加的路径
    paths_to_add = [
        project_root,            # 项目根目录
        src_dir,                 # src目录
        os.path.join(src_dir, "core"),   # 核心模块目录
        os.path.join(src_dir, "gui"),    # GUI模块目录
        os.path.join(project_root, "config"),  # 配置目录
    ]
    
    # 添加路径到sys.path
    for path in paths_to_add:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    
    return True

if __name__ == "__main__":
    setup_paths() 