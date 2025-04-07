#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统计模块 - 记录和展示脱水处理的统计信息
"""

import time
from typing import Dict, List, Optional

# 导入工具函数
try:
    from ..utils import format_time, setup_logger
except ImportError:
    from utils import format_time, setup_logger

# 设置日志记录器
logger = setup_logger(__name__)

# 统计数据全局对象
statistics = {
    "start_time": 0,               # 程序开始时间
    "end_time": 0,                 # 程序结束时间
    "total_files": 0,              # 总文件数
    "success_count": 0,            # 成功处理的文件数
    "failed_count": 0,             # 失败的文件数
    "retry_count": 0,              # 重试的次数
    "file_stats": {},              # 每个文件的统计数据：{文件路径: {"time": 处理时间, "status": 状态, "retries": 重试次数}}
    "condensation_ratios": [],     # 压缩比例列表
    "total_characters_original": 0,  # 原始总字符数
    "total_characters_condensed": 0, # 压缩后总字符数
}

def reset_statistics():
    """重置统计数据"""
    global statistics
    
    statistics["start_time"] = time.time()
    statistics["end_time"] = 0
    statistics["total_files"] = 0
    statistics["success_count"] = 0
    statistics["failed_count"] = 0
    statistics["retry_count"] = 0
    statistics["file_stats"] = {}
    statistics["condensation_ratios"] = []
    statistics["total_characters_original"] = 0
    statistics["total_characters_condensed"] = 0

def update_file_stats(file_path: str, status: str, processing_time: float, 
                    is_first_attempt: bool = True, **kwargs):
    """更新文件处理统计信息
    
    Args:
        file_path: 文件路径
        status: 处理状态 (success, failed, skipped, etc.)
        processing_time: 处理时间(秒)
        is_first_attempt: 是否是首次尝试处理
        **kwargs: 其他统计数据
    """
    global statistics
    
    file_stats = {
        "status": status,
        "time": processing_time,
        "is_first_attempt": is_first_attempt
    }
    
    # 添加其他数据
    for key, value in kwargs.items():
        file_stats[key] = value
    
    # 更新统计对象
    statistics["file_stats"][file_path] = file_stats
    
    # 如果是成功处理，更新相关计数
    if status == "success":
        if is_first_attempt:
            statistics["success_count"] += 1
        
        # 更新字符统计
        if "original_length" in kwargs and "condensed_length" in kwargs:
            statistics["total_characters_original"] += kwargs["original_length"]
            statistics["total_characters_condensed"] += kwargs["condensed_length"]
            
            # 更新压缩比例
            if kwargs["original_length"] > 0:
                ratio = (kwargs["condensed_length"] / kwargs["original_length"]) * 100
                statistics["condensation_ratios"].append(ratio)
    
    # 如果是失败处理，更新失败计数
    elif status == "failed" and is_first_attempt:
        statistics["failed_count"] += 1
    
    # 如果是重试，更新重试计数
    if not is_first_attempt:
        statistics["retry_count"] += 1

def finalize_statistics():
    """完成统计，计算最终结果"""
    global statistics
    
    # 记录结束时间
    statistics["end_time"] = time.time()
    
    # 验证成功和失败的数量
    success_count = sum(1 for stats in statistics["file_stats"].values() 
                       if stats.get("status") in ["success", "success-cached", "success-directory", "success-short"] 
                       and stats.get("is_first_attempt", True))
    
    failed_count = sum(1 for stats in statistics["file_stats"].values() 
                      if stats.get("status") == "failed" and stats.get("is_first_attempt", True))
    
    # 更新统计数据
    statistics["success_count"] = success_count
    statistics["failed_count"] = failed_count

def print_processing_summary(failed_files: Optional[Dict[str, int]] = None) -> None:
    """打印处理结果摘要

    Args:
        failed_files: 失败的文件及重试次数字典，格式为 {file_path: retry_count}
    """
    global statistics
    
    # 计算总运行时间
    total_runtime = statistics["end_time"] - statistics["start_time"]
    
    # 打印分隔线
    print("\n" + "="*50)
    print("处理结果统计")
    print("="*50)
    
    # 基本信息
    print(f"总运行时间: {format_time(total_runtime)}")
    
    if statistics["total_files"] > 0:
        success_rate = (statistics["success_count"]/statistics["total_files"]*100)
        print(f"成功处理: {statistics['success_count']}/{statistics['total_files']} 个文件 (成功率: {success_rate:.1f}%)")
    
    # 重试信息
    if statistics["retry_count"] > 0:
        print(f"重试次数: {statistics['retry_count']} 次")
    
    # 失败文件信息
    if statistics["failed_count"] > 0:
        print(f"处理失败: {statistics['failed_count']} 个文件")
        
        if failed_files:
            print("\n失败的文件列表:")
            for file_path, retries in failed_files.items():
                print(f"  - {file_path} (重试 {retries} 次后仍失败)")
    
    # 压缩统计
    if statistics["condensation_ratios"]:
        avg_ratio = sum(statistics["condensation_ratios"]) / len(statistics["condensation_ratios"])
        min_ratio = min(statistics["condensation_ratios"])
        max_ratio = max(statistics["condensation_ratios"])
        print(f"\n压缩比例统计:")
        print(f"  - 平均压缩比: {avg_ratio:.1f}%")
        print(f"  - 最小压缩比: {min_ratio:.1f}%")
        print(f"  - 最大压缩比: {max_ratio:.1f}%")
    
    # 字符统计
    if statistics["total_characters_original"] > 0:
        orig_chars = statistics["total_characters_original"]
        cond_chars = statistics["total_characters_condensed"]
        total_ratio = cond_chars / orig_chars * 100
        
        print(f"\n总字符统计:")
        print(f"  - 原文总字符: {orig_chars:,} 字符")
        print(f"  - 脱水后总字符: {cond_chars:,} 字符")
        print(f"  - 整体压缩比: {total_ratio:.1f}%")
    
    # 性能统计
    if statistics["file_stats"]:
        try:
            # 尝试计算平均处理时间，但只考虑有处理时间的成功文件
            first_attempt_times = []
            for _, stats in statistics["file_stats"].items():
                if ("time" in stats and 
                    stats.get("is_first_attempt", True) and 
                    stats.get("status", "").startswith("success")):
                    first_attempt_times.append(stats["time"])
            
            if first_attempt_times:
                avg_time = sum(first_attempt_times) / len(first_attempt_times)
                print(f"\n性能统计:")
                print(f"  - 平均单文件处理时间: {format_time(avg_time)}")
                print(f"  - 处理速度: {60/avg_time:.1f} 个文件/小时")
        except Exception as e:
            logger.warning(f"计算性能统计时出错: {e}")
    
    print("="*50) 