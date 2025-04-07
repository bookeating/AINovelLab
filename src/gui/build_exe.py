#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本 - 将GUI应用程序打包成Windows可执行文件(.exe)

使用PyInstaller将AI小说实验室的GUI界面打包成可执行文件，
便于在没有Python环境的Windows系统上直接运行。

使用方法:
    cd 项目根目录
    python src/gui/build_exe.py
"""

import os
import sys
import shutil
import subprocess
import platform

def main():
    """主函数"""
    print("=" * 60)
    print("AI小说实验室GUI打包脚本")
    print("=" * 60)
    
    # 获取项目根目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(src_dir)
    os.chdir(root_dir)  # 切换到项目根目录
    
    print(f"项目根目录: {root_dir}")
    
    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print("已检测到PyInstaller，版本:", PyInstaller.__version__)
    except ImportError:
        print("未检测到PyInstaller，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller安装成功！")
        except Exception as e:
            print(f"PyInstaller安装失败: {e}")
            print("请手动安装PyInstaller: pip install pyinstaller")
            return
    
    # 清理之前的构建文件
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            print(f"正在清理{dir_name}目录...")
            try:
                shutil.rmtree(dir_name)
            except PermissionError:
                print(f"警告: 无法删除{dir_name}目录，可能被其他程序占用")
                print(f"将尝试在现有目录上继续构建...")
    
    if os.path.exists("AINovelLab.spec"):
        print("正在清理旧的spec文件...")
        try:
            os.remove("AINovelLab.spec")
        except PermissionError:
            print("警告: 无法删除spec文件，可能被其他程序占用")
            print("将使用现有spec文件继续构建...")
    
    # 确保data和resources目录存在
    for dir_name in ["data", "resources"]:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"创建{dir_name}目录...")
    
    # 复制必要文件到打包目录
    required_files = ["requirements.txt", "api_keys.json"]
    for file in required_files:
        if os.path.exists(file):
            print(f"复制{file}到资源目录...")
            
    # 询问是否需要带控制台窗口
    console_mode = input("是否需要显示控制台窗口以便调试(y/n)? [n]: ").lower() == 'y'
    
    # 构建命令
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=AINovelLab",
    ]
    
    # 根据用户选择决定是否显示控制台窗口
    if not console_mode:
        pyinstaller_cmd.append("--windowed")  # 创建窗口应用程序，不显示控制台
    else:
        print("注意: 将创建带控制台窗口的版本，有助于查看错误信息")
    
    # 添加其他选项
    pyinstaller_cmd.extend([
        # 如果有图标文件，取消下面这行的注释
        # "--icon=resources/icon.ico",
        "--add-data=resources;resources",  # 添加资源文件
        "--add-data=data;data",           # 添加数据文件
        "--add-data=config;config",       # 添加配置文件
        "--add-data=api_keys.json;.",     # 添加API密钥文件
        "--add-data=src;src",             # 添加整个src目录
        "--add-data=src/gui;gui",         # 添加GUI模块
        "--hidden-import=PyQt5",          # 确保PyQt5被包含
        "--hidden-import=PyQt5.QtWidgets", # 添加必要的PyQt5子模块
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=ebooklib",       # 添加ebooklib依赖
        "--hidden-import=ebooklib.epub",  # 明确包含ebooklib.epub子模块
        "--hidden-import=bs4",            # 添加BeautifulSoup依赖
        "--hidden-import=bs4.builder",    # 添加BeautifulSoup解析器模块
        "--hidden-import=tqdm",           # 添加tqdm进度条依赖
        "--hidden-import=requests",       # 添加网络请求依赖
        "--hidden-import=lxml",           # 添加lxml XML解析器依赖
        "--noconfirm",  # 不确认覆盖
        "--clean",      # 清理PyInstaller缓存
        "run.py"        # 入口文件
    ])
    
    # 根据操作系统调整文件路径分隔符
    if platform.system() != "Windows":
        for i, item in enumerate(pyinstaller_cmd):
            if ";" in item:
                pyinstaller_cmd[i] = item.replace(";", ":")
    
    # 移除空项
    pyinstaller_cmd = [item for item in pyinstaller_cmd if item]
    
    print("\n正在打包应用程序，这可能需要几分钟时间...")
    print(" ".join(pyinstaller_cmd))
    print("-" * 60)
    
    # 执行PyInstaller命令
    try:
        subprocess.check_call(pyinstaller_cmd)
        print("\n打包成功! 可执行文件位于 dist/AINovelLab/ 目录")
        
        # 创建配置模板文件
        print("正在创建配置模板文件...")
        template_config = {
            "gemini_api": [
                {
                    "key": "你的gemini 密钥",
                    "redirect_url": "代理url 地址，可空。默认：https://generativelanguage.googleapis.com/v1beta/models",
                    "model": "模型，可空。默认：gemini-2.0-flash",
                    "rpm": 10
                },{
                    "key":"最简配置demo"
                }
            ],
            "openai_api": [
                {
                    "key": "你的openai 密钥或其他一切兼容openai-api 格式的,如DeepSeek等",
                    "redirect_url": "代理url，可空。默认：https://api.openai.com/v1/chat/completions",
                    "model": "模型，可空。默认：gpt-3.5-turbo",
                    "rpm": 10
                },{
                    "key":"最简配置demo"
                }
            ],
            "max_rpm": 20
        }
        
        import json
        output_dir = os.path.join("dist", "AINovelLab")
        template_path = os.path.join(output_dir, "api_keys.json")
        
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(template_config, f, indent=4, ensure_ascii=False)
        
        print(f"配置模板文件已创建: {template_path}")
        
        # 创建调试运行批处理文件 - 仅在非控制台模式下创建
        if not console_mode:
            debug_bat_path = os.path.join(output_dir, "debug_run.bat")
            with open(debug_bat_path, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("chcp 65001\n")  # 设置控制台代码页为UTF-8
                f.write("echo 开始调试模式运行 AINovelLab\n")
                f.write("echo 如有错误将显示在此窗口\n")
                f.write("echo -----------------------------------\n")
                f.write("echo 正在将版本模块复制到可访问位置...\n")
                f.write("if exist .\\src\\version.py copy .\\src\\version.py .\\version.py >nul\n")
                f.write("echo -----------------------------------\n")
                f.write("AINovelLab.exe\n")
                f.write("set ERROR_CODE=%ERRORLEVEL%\n")
                f.write("echo -----------------------------------\n")
                f.write("echo 程序已退出，错误代码: %ERROR_CODE%\n")
                f.write("if %ERROR_CODE% NEQ 0 (\n")
                f.write("    echo 发生错误！以下是可能的原因：\n")
                f.write("    echo 1. 缺少必要的DLL文件 - 安装VC++ Redistributable\n")
                f.write("    echo 2. 无法找到必要的Python模块 - 尝试重新打包\n")
                f.write("    echo 3. 版本信息模块导入失败 - 检查src/version.py文件\n")
                f.write(")\n")
                f.write("pause\n")
            
            print(f"调试批处理文件已创建: {debug_bat_path}")
        
        print("\n提示：")
        print("1. api_keys.json模板文件已创建，请根据需要修改API密钥")
        print("2. 将api_keys.json放在可执行文件同级目录可以方便修改API密钥")
        if not console_mode:
            print("3. 如果程序无法启动，请运行debug_run.bat查看错误信息")
        print("4. 如果出现'无法启动此程序，因为系统中丢失xxx.dll'错误，请安装Microsoft Visual C++ Redistributable")
        print("5. 建议安装最新版本的Visual C++ Redistributable和Universal C Runtime")
        print("6. 下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    except Exception as e:
        print(f"\n打包失败: {e}")
        print("请检查错误信息并重试")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 