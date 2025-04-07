#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说脱水工具入口脚本 - 调用core/novel_condenser包处理小说
"""

import os
import sys

# 将当前目录的父目录添加到系统路径中，以便导入其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    # 尝试导入脱水工具模块
    from src.core.novel_condenser.main import main
    
    # 运行主程序
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保您已正确安装所需的依赖项")
    print("可以通过运行以下命令安装依赖:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"运行时错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 