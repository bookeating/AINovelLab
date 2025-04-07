#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
临时打包脚本 - 使用不同的输出目录名称避免权限问题
"""

import os
import sys
import subprocess
import platform

def main():
    """主函数"""
    print("=" * 60)
    print("AI小说实验室GUI临时打包脚本")
    print("=" * 60)
    
    # 获取项目根目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(src_dir)
    os.chdir(root_dir)  # 切换到项目根目录
    
    print(f"项目根目录: {root_dir}")
    
    # 构建命令 - 使用不同的输出名称和不删除现有文件
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=AINovelLab_New",  # 使用新名称避免冲突
        "--add-data=resources;resources",
        "--add-data=data;data",
        "--add-data=config;config",
        "--add-data=api_keys.json;.",
        "--add-data=src;src",
        "--add-data=src/gui;gui",
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=ebooklib",
        "--hidden-import=ebooklib.epub",  # 明确包含ebooklib.epub子模块
        "--hidden-import=bs4",
        "--hidden-import=tqdm",
        "--hidden-import=requests",
        "--noconfirm",
        "run.py"
    ]
    
    # 根据操作系统调整文件路径分隔符
    if platform.system() != "Windows":
        for i, item in enumerate(pyinstaller_cmd):
            if ";" in item:
                pyinstaller_cmd[i] = item.replace(";", ":")
    
    print("\n正在打包应用程序，这可能需要几分钟时间...")
    print(" ".join(pyinstaller_cmd))
    print("-" * 60)
    
    # 执行PyInstaller命令
    try:
        subprocess.check_call(pyinstaller_cmd)
        print("\n打包成功! 可执行文件位于 dist/AINovelLab_New/ 目录")
        
        # 创建调试运行批处理文件
        output_dir = os.path.join("dist", "AINovelLab_New")
        debug_bat_path = os.path.join(output_dir, "debug_run.bat")
        with open(debug_bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("echo 开始调试模式运行 AINovelLab\n")
            f.write("echo 如有错误将显示在此窗口\n")
            f.write("echo -----------------------------------\n")
            f.write("AINovelLab_New.exe\n")
            f.write("echo -----------------------------------\n")
            f.write("echo 程序已退出，错误代码: %ERRORLEVEL%\n")
            f.write("pause\n")
        
        print(f"调试批处理文件已创建: {debug_bat_path}")
        
    except Exception as e:
        print(f"\n打包失败: {e}")
        print("请检查错误信息并重试")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 