#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI小说实验室启动脚本
"""

import os
import sys
import traceback

def main():
    """主入口函数"""
    # 获取当前目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 添加项目目录到Python路径
    sys.path.insert(0, current_dir)
    
    # 打印当前路径和sys.path，用于调试
    print(f"当前目录: {current_dir}")
    print(f"Python路径: {sys.path}")
    
    # 检测是否在打包环境中运行
    is_frozen = getattr(sys, 'frozen', False)
    print(f"是否在打包环境中运行: {is_frozen}")
    
    # 对于打包环境，调整导入策略
    if is_frozen:
        # 直接导入主窗口，跳过src模块导入
        try:
            from gui.main_window import MainWindow
            import PyQt5.QtWidgets as QtWidgets
            
            app = QtWidgets.QApplication(sys.argv)
            window = MainWindow()
            window.show()
            sys.exit(app.exec_())
        except ImportError as e:
            print(f"打包环境导入错误: {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        # 开发环境中的导入方式
        try:
            # 导入导入辅助模块并设置路径
            import src.import_helper as helper
            helper.setup_paths()
            
            # 导入并启动主程序
            from src.main import main as start_app
            start_app()
        except ImportError as e:
            print(f"错误: 无法导入核心模块，请检查项目结构。详细错误: {e}")
            traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            print(f"启动错误: {e}")
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main() 