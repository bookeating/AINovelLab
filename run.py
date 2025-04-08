#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI小说工具启动脚本
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
    
    # 确保版本模块可用
    try:
        # 检查版本文件是否存在
        import importlib.util
        version_paths = [
            os.path.join(current_dir, 'version.py'),
            os.path.join(current_dir, 'src', 'version.py')
        ]
        
        version_found = False
        for version_path in version_paths:
            if os.path.exists(version_path):
                print(f"找到版本文件: {version_path}")
                version_found = True
                # 如果运行在冻结环境中，复制版本文件到根目录以确保可以导入
                if is_frozen and not os.path.exists(os.path.join(current_dir, 'version.py')):
                    try:
                        import shutil
                        shutil.copy(version_path, os.path.join(current_dir, 'version.py'))
                        print("已复制版本文件到根目录以确保可访问")
                    except Exception as e:
                        print(f"复制版本文件时出错: {e}")
        
        if not version_found:
            print("警告: 未找到版本文件")
    except Exception as e:
        print(f"检查版本文件时出错: {e}")
    
    # 对于打包环境，调整导入策略
    if is_frozen:
        # 直接导入主窗口，跳过src模块导入
        try:
            print("在打包环境中导入GUI组件...")
            from gui.main_window import MainWindow
            import PyQt5.QtWidgets as QtWidgets
            
            # 确保样式模块可用
            try:
                from gui.style import get_material_style
                print("样式模块加载成功")
            except ImportError as style_error:
                print(f"警告：无法导入样式模块，界面可能不会正确显示。错误：{style_error}")
            
            app = QtWidgets.QApplication(sys.argv)
            
            # 应用样式表
            try:
                from gui.style import get_material_style
                print("应用样式表...")
                app.setStyleSheet(get_material_style())
            except Exception as style_error:
                print(f"应用样式表失败：{style_error}")
            
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
            print("在开发环境中启动应用程序...")
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