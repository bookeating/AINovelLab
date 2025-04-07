#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具模块 - 提供项目通用的工具函数和类
"""

import logging
import os
import re
import time
from pathlib import Path

def setup_logger(name=None, log_level=logging.INFO):
    """配置并返回日志记录器

    Args:
        name: 日志记录器名称，默认为None（使用root logger）
        log_level: 日志级别，默认为INFO

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(name)

def get_safe_filename(text, max_length=50):
    """将文本转换为安全的文件名
    
    Args:
        text: 原始文本
        max_length: 文件名最大长度，默认50
    
    Returns:
        str: 处理后的安全文件名
    """
    if not text:
        return "unnamed"
        
    # 移除不适合作为文件名的字符
    unsafe_chars = r'[\\/*?:"<>|]'
    safe_text = re.sub(unsafe_chars, '', text)
    
    # 替换空白字符为下划线
    safe_text = re.sub(r'\s+', '_', safe_text)
    
    # 限制长度，避免文件名过长
    if len(safe_text) > max_length:
        safe_text = safe_text[:max_length-3] + '...'
        
    return safe_text

def format_time(seconds: float) -> str:
    """格式化时间为易读形式
    
    Args:
        seconds: 时间秒数
        
    Returns:
        str: 格式化后的时间字符串
    """
    if seconds < 60:
        return f"{seconds:.2f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}小时"

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建

    Args:
        directory: 目录路径

    Returns:
        Path: 目录路径对象
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def read_text_file(file_path, encodings=None):
    """读取文本文件，自动尝试不同编码
    
    Args:
        file_path: 文件路径
        encodings: 要尝试的编码列表，默认为常见中文编码
        
    Returns:
        str: 文件内容，读取失败则返回空字符串
    """
    logger = logging.getLogger(__name__)
    
    if encodings is None:
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
    
    file_path = Path(file_path)
    
    for encoding in encodings:
        try:
            logger.debug(f"尝试使用 {encoding} 编码读取文件 {file_path.name}")
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                logger.debug(f"文件 {file_path.name} 使用 {encoding} 编码成功读取")
                return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"读取文件 {file_path} 时发生错误: {e}")
            break
    
    logger.warning(f"警告：无法解码文件 {file_path}，将跳过该文件")
    return "" 