#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说脱水工具主模块 - 提供命令行接口和处理流程控制
"""

import argparse
import concurrent.futures
import os
import sys
import threading
import time
import queue
from typing import Dict, List, Optional, Tuple

# 导入模块
try:
    from . import config
    from .key_manager import APIKeyManager
    from .file_utils import (
        read_file, is_directory_file, save_condensed_novel, 
        save_directory_file, find_matching_files, get_output_file_path,
        get_cached_content, create_cache_for_file
    )
    from .api_service import condense_novel_gemini, condense_novel_openai, print_processing_stats
    from .stats import statistics, reset_statistics, update_file_stats, finalize_statistics, print_processing_summary
    from ..utils import setup_logger
except ImportError:
    import config
    from key_manager import APIKeyManager
    from file_utils import (
        read_file, is_directory_file, save_condensed_novel, 
        save_directory_file, find_matching_files, get_output_file_path,
        get_cached_content, create_cache_for_file
    )
    from api_service import condense_novel_gemini, condense_novel_openai, print_processing_stats
    from stats import statistics, reset_statistics, update_file_stats, finalize_statistics, print_processing_summary
    from utils import setup_logger

# 创建日志记录器
logger = setup_logger(__name__)

# 全局变量
OUTPUT_DIR = None  # 输出目录
gemini_key_manager = None  # Gemini API密钥管理器
openai_key_manager = None  # OpenAI API密钥管理器

def process_single_file(file_path, api_type="gemini", api_key_config=None, file_index=None, total_files=None, retry_attempt=0, force_regenerate=False):
    """处理单个文件
    
    Args:
        file_path: 文件路径
        api_type: API类型，"gemini"或"openai"
        api_key_config: API密钥配置
        file_index: 当前文件索引
        total_files: 总文件数
        retry_attempt: 当前重试次数
        force_regenerate: 是否强制重新生成
    
    Returns:
        处理成功返回True，处理失败返回False
    """
    global gemini_key_manager, openai_key_manager
    
    # 获取开始时间
    local_start_time = time.time()
    
    try:
        base_name = os.path.basename(file_path)
        output_file = get_output_file_path(file_path)
        
        # 显示处理信息
        if file_index is not None and total_files is not None:
            if retry_attempt > 0:
                logger.info(f"\n第 {retry_attempt} 次重试处理 [{file_index}/{total_files}]: {base_name}")
            else:
                logger.info(f"\n处理文件 [{file_index}/{total_files}]: {base_name}")
        else:
            logger.info(f"\n处理文件: {base_name}")
        
        # 检查输出文件是否已存在
        if os.path.exists(output_file) and not force_regenerate:
            # 检查现有文件大小和内容质量
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                # 检查文件是否过小或为空
                if len(existing_content) < 300:
                    logger.info(f"已存在的脱水文件 {base_name} 小于300个字符，将重新脱水")
                    try:
                        os.remove(output_file)
                    except:
                        logger.warning(f"删除已存在的小文件失败: {output_file}")
                elif "错误" in existing_content[:100] or "失败" in existing_content[:100]:
                    # 如果文件开头包含错误信息，也重新处理
                    logger.info(f"已存在的脱水文件 {base_name} 包含错误信息，将重新脱水")
                    try:
                        os.remove(output_file)
                    except:
                        logger.warning(f"删除已存在的错误文件失败: {output_file}")
                else:
                    if retry_attempt > 0:
                        logger.info(f"跳过第 {retry_attempt} 次重试的已处理文件: {base_name}")
                    else:
                        logger.info(f"跳过已处理文件: {base_name}")
                    
                    # 记录处理时间并更新统计信息
                    process_time = time.time() - local_start_time
                    update_file_stats(
                        file_path, 
                        "skipped", 
                        process_time, 
                        is_first_attempt=(retry_attempt == 0)
                    )
                    
                    return True
            except Exception as e:
                logger.warning(f"检查已存在文件时出错: {str(e)}，将重新脱水")
                # 如果读取文件出错，尝试删除并重新处理
                try:
                    os.remove(output_file)
                except:
                    pass
        
        # 读取文件内容
        try:
            content = read_file(file_path)
        except Exception as e:
            logger.error(f"无法读取文件内容: {file_path}, 错误: {str(e)}")
            
            # 更新统计信息
            process_time = time.time() - local_start_time
            update_file_stats(
                file_path, 
                "error", 
                process_time, 
                is_first_attempt=(retry_attempt == 0),
                error=str(e)
            )
            
            return False
        
        if not content:
            logger.warning(f"文件内容为空: {file_path}")
            
            # 更新统计信息
            process_time = time.time() - local_start_time
            update_file_stats(
                file_path, 
                "empty", 
                process_time, 
                is_first_attempt=(retry_attempt == 0)
            )
            
            return False
        
        # 尝试使用缓存
        if not force_regenerate:
            cached_content = get_cached_content(file_path)
            if cached_content:
                logger.info(f"使用缓存的处理结果: {base_name}")
                save_condensed_novel(file_path, cached_content)
                
                # 记录处理时间
                process_time = time.time() - local_start_time
                
                # 更新统计信息
                update_file_stats(
                    file_path, 
                    "success-cached", 
                    process_time, 
                    is_first_attempt=(retry_attempt == 0),
                    original_length=len(content),
                    condensed_length=len(cached_content)
                )
                
                # 如果显示进度，输出完成信息
                if file_index is not None and total_files is not None:
                    logger.info(f"[{file_index}/{total_files}] 使用缓存处理完成")
                
                return True
        
        # 检查是否是目录文件
        if is_directory_file(content):
            logger.info(f"检测到目录文件，直接保存: {base_name}")
            save_directory_file(file_path)
            
            # 记录处理时间
            process_time = time.time() - local_start_time
            
            # 更新统计信息
            update_file_stats(
                file_path, 
                "success-directory", 
                process_time, 
                is_first_attempt=(retry_attempt == 0)
            )
            
            return True
        
        # 检查内容是否需要处理（太短的内容不处理）
        if len(content) < 100:
            logger.info(f"内容太短，不需要脱水: {base_name}")
            save_condensed_novel(file_path, content)
            
            # 记录处理时间
            process_time = time.time() - local_start_time
            
            # 更新统计信息
            update_file_stats(
                file_path, 
                "success-short", 
                process_time, 
                is_first_attempt=(retry_attempt == 0)
            )
            
            return True
        
        # 调用API进行脱水
        # 创建重试机制，最多尝试3次不同的API密钥
        max_api_attempts = 3
        success = False
        result = None
        all_keys_skipped = False
        
        # 确保使用全局API密钥管理器
        if api_type == "gemini":
            if gemini_key_manager is None:
                logger.warning("全局Gemini API密钥管理器未初始化，正在创建新实例")
                gemini_key_manager = APIKeyManager(config.GEMINI_API_CONFIG, config.DEFAULT_MAX_RPM)
            
            for api_attempt in range(max_api_attempts):
                if api_attempt > 0:
                    logger.debug(f"尝试使用新的Gemini API密钥进行第{api_attempt+1}次尝试...")
                    api_key_config = None  # 重新获取密钥
                
                # 确保始终传递gemini_key_manager给API服务
                result = condense_novel_gemini(content, api_key_config, gemini_key_manager)
                
                # 检查是否因为所有密钥都被跳过而失败
                if result is None and gemini_key_manager and hasattr(gemini_key_manager, 'skipped_keys'):
                    valid_keys = [conf['key'] for conf in gemini_key_manager.api_configs 
                                  if conf['key'] not in gemini_key_manager.skipped_keys]
                    if not valid_keys:
                        all_keys_skipped = True
                        logger.warning(f"处理文件 {base_name} 失败：所有Gemini API密钥都因失败次数过多而被跳过")
                        break
                
                if result:
                    success = True
                    break
                elif gemini_key_manager and api_key_config:
                    # 报告当前密钥错误
                    gemini_key_manager.report_error(api_key_config['key'])
        
        elif api_type == "openai":
            if openai_key_manager is None:
                logger.warning("全局OpenAI API密钥管理器未初始化，正在创建新实例")
                openai_key_manager = APIKeyManager(config.OPENAI_API_CONFIG, config.DEFAULT_MAX_RPM)
            
            for api_attempt in range(max_api_attempts):
                if api_attempt > 0:
                    logger.debug(f"尝试使用新的OpenAI API密钥进行第{api_attempt+1}次尝试...")
                    api_key_config = None  # 重新获取密钥
                
                # 确保始终传递openai_key_manager给API服务
                result = condense_novel_openai(content, api_key_config, openai_key_manager)
                
                # 检查是否因为所有密钥都被跳过而失败
                if result is None and openai_key_manager and hasattr(openai_key_manager, 'skipped_keys'):
                    valid_keys = [conf['key'] for conf in openai_key_manager.api_configs 
                                  if conf['key'] not in openai_key_manager.skipped_keys]
                    if not valid_keys:
                        all_keys_skipped = True
                        logger.warning(f"处理文件 {base_name} 失败：所有OpenAI API密钥都因失败次数过多而被跳过")
                        break
                
                if result:
                    success = True
                    break
                elif openai_key_manager and api_key_config:
                    # 报告当前密钥错误
                    openai_key_manager.report_error(api_key_config['key'])
        
        if success and result:
            # 保存脱水后的内容
            save_condensed_novel(file_path, result)
            
            # 创建缓存
            create_cache_for_file(content, result, file_path)
            
            # 如果API密钥管理器存在，报告成功
            if gemini_key_manager and api_key_config:
                gemini_key_manager.report_success(api_key_config)
            
            # 记录处理时间
            process_time = time.time() - local_start_time
            
            # 更新统计信息
            # 计算压缩比例
            condensation_ratio = (len(result) / len(content)) * 100 if len(content) > 0 else 0
            
            update_file_stats(
                file_path, 
                "success", 
                process_time, 
                is_first_attempt=(retry_attempt == 0),
                original_length=len(content),
                condensed_length=len(result),
                condensation_ratio=condensation_ratio
            )
            
            # 如果显示进度，输出完成信息
            if file_index is not None and total_files is not None:
                logger.info(f"[{file_index}/{total_files}] 处理完成")
            
            return True
        else:
            if all_keys_skipped:
                logger.error(f"处理失败: {base_name}，所有API密钥都因失败次数过多而被跳过，脱水过程结束")
                error_msg = f"# 脱水处理失败\n\n原因: 所有API密钥都因失败次数过多而被跳过\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n请检查API密钥或稍后重试。"
            else:
                logger.error(f"处理失败: {base_name}，已尝试{max_api_attempts}个不同API密钥")
                error_msg = f"# 脱水处理失败\n\n原因: API处理失败\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n请重试或联系管理员。"
            
            # 尝试保存错误信息
            try:
                save_condensed_novel(file_path, error_msg)
            except:
                pass
            
            # 记录处理时间
            process_time = time.time() - local_start_time
            
            # 更新统计信息
            update_file_stats(
                file_path, 
                "failed", 
                process_time, 
                is_first_attempt=(retry_attempt == 0),
                api_attempts=max_api_attempts,
                all_keys_skipped=all_keys_skipped
            )
            
            return False
        
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        
        # 记录处理时间
        process_time = time.time() - local_start_time
        
        # 更新统计信息
        update_file_stats(
            file_path, 
            "error", 
            process_time, 
            is_first_attempt=(retry_attempt == 0),
            error=str(e)
        )
            
        return False

def process_files_sequentially(file_paths: List[str], total_files: int, 
                          api_type: str = "gemini", force_regenerate: bool = False, retry_attempt: int = 0) -> Tuple[int, Dict[str, int]]:
    """顺序处理文件
    
    Args:
        file_paths: 文件路径列表
        total_files: 总文件数
        api_type: API类型，gemini或openai
        force_regenerate: 是否强制重新生成
        retry_attempt: 当前重试次数
    
    Returns:
        成功处理的文件数和失败的文件字典
    """
    success_count = 0
    failed_files = {}
    
    for i, file_path in enumerate(file_paths):
        try:
            status = process_single_file(
                file_path, 
                api_type=api_type, 
                file_index=i+1, 
                total_files=total_files, 
                retry_attempt=retry_attempt,
                force_regenerate=force_regenerate
            )
            
            if status:
                success_count += 1
            else:
                failed_files[file_path] = 0
                
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {str(e)}")
            failed_files[file_path] = 0
    
    return success_count, failed_files

def process_files_concurrently(files_to_process: List[str], max_workers: int, api_type: str = "gemini", force_regenerate=False, update_progress_func=None):
    """并发处理文件
    
    Args:
        files_to_process: 文件路径列表
        max_workers: 最大工作线程数
        api_type: API类型，gemini, openai 或 mixed
        force_regenerate: 是否强制重新生成
        update_progress_func: 更新进度的回调函数
    
    Returns:
        成功处理的文件数和失败的文件字典
    """
    global gemini_key_manager, openai_key_manager
    success_count = 0
    failed_files = {}
    completed_count = 0
    total_files = len(files_to_process)
    
    # 线程锁，用于更新计数
    lock = threading.Lock()
    
    # 用于标记是否所有密钥都被跳过
    all_gemini_keys_skipped = False
    all_openai_keys_skipped = False
    keys_skipped_lock = threading.Lock()
    
    # 进度更新器线程
    progress_stopped = threading.Event()
    
    # 定义文件处理函数
    def process_file(file_path, file_index):
        nonlocal success_count, completed_count, all_gemini_keys_skipped, all_openai_keys_skipped
        
        # 确保全局key_manager已初始化
        global gemini_key_manager, openai_key_manager
        
        # 初始化Gemini API密钥管理器（如果使用Gemini或混合模式）
        if (api_type == "gemini" or api_type == "mixed") and gemini_key_manager is None:
            with keys_skipped_lock:
                if gemini_key_manager is None:
                    logger.warning("并发处理中检测到全局Gemini API密钥管理器未初始化，正在创建")
                    gemini_key_manager = APIKeyManager(config.GEMINI_API_CONFIG, config.DEFAULT_MAX_RPM)
        
        # 初始化OpenAI API密钥管理器（如果使用OpenAI或混合模式）
        if (api_type == "openai" or api_type == "mixed") and openai_key_manager is None:
            with keys_skipped_lock:
                if openai_key_manager is None:
                    logger.warning("并发处理中检测到全局OpenAI API密钥管理器未初始化，正在创建")
                    openai_key_manager = APIKeyManager(config.OPENAI_API_CONFIG, config.DEFAULT_MAX_RPM)
        
        # 检查是否要跳过处理
        with keys_skipped_lock:
            if api_type == "gemini" and all_gemini_keys_skipped:
                return False
            elif api_type == "openai" and all_openai_keys_skipped:
                return False
            elif api_type == "mixed" and all_gemini_keys_skipped and all_openai_keys_skipped:
                return False
        
        try:
            # 如果是混合模式，根据文件索引选择不同的API
            current_api_type = api_type
            if api_type == "mixed":
                # 检查是否有一种API的密钥已全部跳过
                with keys_skipped_lock:
                    if all_gemini_keys_skipped and not all_openai_keys_skipped:
                        current_api_type = "openai"
                    elif all_openai_keys_skipped and not all_gemini_keys_skipped:
                        current_api_type = "gemini"
                    else:
                        # 使用文件索引的奇偶性来分配API，偶数使用Gemini，奇数使用OpenAI
                        current_api_type = "gemini" if file_index % 2 == 0 else "openai"
                
                logger.info(f"混合模式: 文件 {os.path.basename(file_path)} 使用 {current_api_type.upper()} API")
            
            # 处理单个文件
            status = process_single_file(
                file_path, 
                api_type=current_api_type,
                file_index=file_index, 
                total_files=total_files,
                force_regenerate=force_regenerate
            )
            
            # 更新计数
            with lock:
                completed_count += 1
                if status:
                    success_count += 1
                else:
                    failed_files[file_path] = 0
                
                # 更新进度
                if update_progress_func:
                    if api_type == "mixed":
                        update_progress_func(completed_count, total_files, f"使用{current_api_type.upper()}")
                    else:
                        update_progress_func(completed_count, total_files)
                    
            # 检查Gemini API密钥状态（如果使用Gemini或混合模式）
            if (current_api_type == "gemini" or api_type == "mixed") and gemini_key_manager and hasattr(gemini_key_manager, 'skipped_keys'):
                valid_keys = [conf['key'] for conf in gemini_key_manager.api_configs 
                              if conf['key'] not in gemini_key_manager.skipped_keys]
                if not valid_keys:
                    with keys_skipped_lock:
                        all_gemini_keys_skipped = True
                        logger.warning("所有Gemini API密钥都已因失败次数过多而被跳过")
                        
                        # 如果是混合模式，检查是否需要停止处理
                        if api_type == "mixed" and all_openai_keys_skipped:
                            logger.warning("所有API密钥都已因失败次数过多而被跳过，停止剩余处理")
                        elif api_type == "gemini":
                            logger.warning("所有Gemini API密钥都已被跳过，停止剩余处理")
            
            # 检查OpenAI API密钥状态（如果使用OpenAI或混合模式）
            if (current_api_type == "openai" or api_type == "mixed") and openai_key_manager and hasattr(openai_key_manager, 'skipped_keys'):
                valid_keys = [conf['key'] for conf in openai_key_manager.api_configs 
                              if conf['key'] not in openai_key_manager.skipped_keys]
                if not valid_keys:
                    with keys_skipped_lock:
                        all_openai_keys_skipped = True
                        logger.warning("所有OpenAI API密钥都已因失败次数过多而被跳过")
                        
                        # 如果是混合模式，检查是否需要停止处理
                        if api_type == "mixed" and all_gemini_keys_skipped:
                            logger.warning("所有API密钥都已因失败次数过多而被跳过，停止剩余处理")
                        elif api_type == "openai":
                            logger.warning("所有OpenAI API密钥都已被跳过，停止剩余处理")
            
            return status
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {str(e)}")
            
            # 更新计数
            with lock:
                completed_count += 1
                failed_files[file_path] = 0
                
                # 更新进度
                if update_progress_func:
                    update_progress_func(completed_count, total_files)
                    
            return False
    
    # 使用tqdm显示进度条
    from tqdm import tqdm
    with tqdm(total=total_files, desc="处理进度") as pbar:
        try:
            # 使用ThreadPoolExecutor处理文件
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 创建future到文件索引的映射
                futures = {}
                for i, file_path in enumerate(files_to_process):
                    future = executor.submit(process_file, file_path, i+1)
                    futures[future] = i
                
                # 处理完成的future
                for future in concurrent.futures.as_completed(futures):
                    # 更新进度条
                    pbar.n = completed_count
                    pbar.refresh()
                    
                    # 检查是否需要提前结束
                    if progress_stopped.is_set():
                        # 尝试取消剩余任务（注意：已开始执行的任务无法取消）
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break
        
        except KeyboardInterrupt:
            logger.warning("用户中断处理")
            # 将未完成的文件标记为失败
            for file_path in files_to_process:
                if file_path not in failed_files and files_to_process.index(file_path) >= completed_count:
                    failed_files[file_path] = 0
    
    # 检查是否因所有密钥都被跳过而提前结束
    all_api_keys_skipped = False
    if api_type == "gemini" and all_gemini_keys_skipped:
        all_api_keys_skipped = True
    elif api_type == "openai" and all_openai_keys_skipped:
        all_api_keys_skipped = True
    elif api_type == "mixed" and all_gemini_keys_skipped and all_openai_keys_skipped:
        all_api_keys_skipped = True
        
    if all_api_keys_skipped:
        logger.warning("脱水过程已终止: 所有可用API密钥都因失败次数过多而被跳过")
        # 将剩余未处理的文件标记为失败
        with lock:
            for i, file_path in enumerate(files_to_process):
                if i >= completed_count:
                    failed_files[file_path] = 0
    
    # 打印最终统计信息
    logger.info(f"处理完成: 总计 {total_files} 个文件, 成功 {success_count} 个, 失败 {len(failed_files)} 个")
    
    return success_count, failed_files

def check_api_keys(api_type="gemini") -> None:
    """检查API密钥是否有效
    
    Args:
        api_type: API类型，"gemini"、"openai"或"mixed"
    """
    # 加载配置
    loaded = config.load_api_config()
    if not loaded:
        logger.error("无法加载API密钥配置")
        return
    
    valid_gemini_key = None
    valid_openai_key = None
    
    # 检查Gemini API密钥（如果是gemini或mixed模式）
    if api_type == "gemini" or api_type == "mixed":
        if not config.GEMINI_API_CONFIG:
            logger.error("未找到有效的Gemini API配置")
            if api_type == "gemini":
                return
        else:
            # 测试每个密钥
            logger.info(f"开始测试 {len(config.GEMINI_API_CONFIG)} 个Gemini API密钥...")
            
            # 简单测试文本
            test_content = "这是一个测试。请将这句话压缩一下。"
            
            for i, key_config in enumerate(config.GEMINI_API_CONFIG):
                key_id = key_config.get('key', '未指定')
                # 仅显示密钥的前8位，保护隐私
                masked_key = key_id[:8] + "..." if len(key_id) > 8 else key_id
                
                logger.info(f"测试Gemini密钥 {i+1}/{len(config.GEMINI_API_CONFIG)}: {masked_key}")
                
                try:
                    # 尝试使用这个密钥进行简单请求
                    result = condense_novel_gemini(test_content, key_config, gemini_key_manager)
                    if result:
                        logger.info(f"✓ Gemini密钥 {masked_key} 有效")
                        logger.info(f"  返回结果: {result}")
                        # 记录有效密钥
                        valid_gemini_key = key_config
                        # 如果只是测试Gemini，直接返回
                        if api_type == "gemini":
                            return valid_gemini_key
                        # 如果是混合模式，继续测试OpenAI
                        break
                    else:
                        logger.error(f"✗ Gemini密钥 {masked_key} 无法获取有效响应")
                except Exception as e:
                    logger.error(f"✗ Gemini密钥 {masked_key} 测试失败: {e}")
    
    # 检查OpenAI API密钥（如果是openai或mixed模式）
    if api_type == "openai" or api_type == "mixed":
        if not config.OPENAI_API_CONFIG:
            logger.error("未找到有效的OpenAI API配置")
            if api_type == "openai":
                return
        else:
            # 测试每个密钥
            logger.info(f"开始测试 {len(config.OPENAI_API_CONFIG)} 个OpenAI API密钥...")
            
            # 简单测试文本
            test_content = "这是一个测试。请将这句话压缩一下。"
            
            for i, key_config in enumerate(config.OPENAI_API_CONFIG):
                key_id = key_config.get('key', '未指定')
                # 仅显示密钥的前8位，保护隐私
                masked_key = key_id[:8] + "..." if len(key_id) > 8 else key_id
                
                logger.info(f"测试OpenAI密钥 {i+1}/{len(config.OPENAI_API_CONFIG)}: {masked_key}")
                
                try:
                    # 尝试使用这个密钥进行简单请求
                    result = condense_novel_openai(test_content, key_config, openai_key_manager)
                    if result:
                        logger.info(f"✓ OpenAI密钥 {masked_key} 有效")
                        logger.info(f"  返回结果: {result}")
                        # 记录有效密钥
                        valid_openai_key = key_config
                        # 如果只是测试OpenAI，直接返回
                        if api_type == "openai":
                            return valid_openai_key
                        # 如果是混合模式，已经测试完成
                        break
                    else:
                        logger.error(f"✗ OpenAI密钥 {masked_key} 无法获取有效响应")
                except Exception as e:
                    logger.error(f"✗ OpenAI密钥 {masked_key} 测试失败: {e}")
    
    # 如果是混合模式，返回测试结果
    if api_type == "mixed":
        if valid_gemini_key and valid_openai_key:
            logger.info("✓ 成功找到有效的Gemini和OpenAI API密钥，混合模式可用")
            return (valid_gemini_key, valid_openai_key)
        elif valid_gemini_key:
            logger.warning("! 仅找到有效的Gemini API密钥，将只使用Gemini API")
            return valid_gemini_key
        elif valid_openai_key:
            logger.warning("! 仅找到有效的OpenAI API密钥，将只使用OpenAI API")
            return valid_openai_key
    
    # 未找到可用的API密钥
    logger.error(f"未找到可用的{api_type.capitalize()} API密钥")
    return None

def main():
    """主函数：解析命令行参数并执行对应操作"""
    global OUTPUT_DIR, gemini_key_manager, openai_key_manager
    
    # 重置统计数据
    reset_statistics()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='小说脱水工具 - 使用LLM将小说内容缩短至30%-50%')
    
    # 输入参数
    input_group = parser.add_argument_group('输入选项')
    input_group.add_argument('input', nargs='?', help='输入文件或目录路径')
    input_group.add_argument('-p', '--pattern', help='文件匹配模式，如 "第*.txt"')
    input_group.add_argument('-r', '--range', help='处理范围，格式为"start-end"，例如"1-10"表示处理第1到第10章')
    
    # 输出参数
    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument('-o', '--output', help='输出目录，默认为"input_脱水"')
    output_group.add_argument('-f', '--force', action='store_true', help='强制重新处理已存在的文件')
    
    # 配置参数
    config_group = parser.add_argument_group('配置选项')
    config_group.add_argument('-c', '--config', help=f'配置文件路径，默认为 {config.CONFIG_FILE_PATH}')
    config_group.add_argument('-k', '--key', help='直接指定Gemini API密钥（优先级高于配置文件）')
    config_group.add_argument('--openai-key', help='直接指定OpenAI API密钥（优先级高于配置文件）')
    config_group.add_argument('--api', choices=['gemini', 'openai', 'mixed'], default='mixed', help='选择使用的API类型，默认为混合模式')
    
    # 执行模式参数
    mode_group = parser.add_argument_group('执行模式')
    mode_group.add_argument('-s', '--sequential', action='store_true', help='使用顺序处理模式，不使用并发处理')
    mode_group.add_argument('-m', '--max-workers', type=int, help='最大并发工作线程数，默认为自动确定')
    mode_group.add_argument('-t', '--test', action='store_true', help='测试模式，只处理前5个文件')
    mode_group.add_argument('--create-config', action='store_true', help='创建配置文件模板')
    mode_group.add_argument('--check-api', action='store_true', help='检查API密钥有效性')
    
    # 调试选项
    debug_group = parser.add_argument_group('调试选项')
    debug_group.add_argument('-d', '--debug', action='store_true', help='启用调试模式，显示详细日志')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='显示更多处理信息')
    
    args = parser.parse_args()
    
    # 处理特殊命令：创建配置模板
    if args.create_config:
        config.create_config_template(args.config)
        return
    
    # 处理特殊命令：检查API密钥
    if args.check_api:
        # 加载配置
        config.load_api_config(args.config)
        # 如果命令行提供了密钥，直接使用
        if args.key:
            config.GEMINI_API_CONFIG = [{"key": args.key}]
        if args.openai_key:
            config.OPENAI_API_CONFIG = [{"key": args.openai_key}]
            
        check_api_keys(args.api)
        return
    
    # 加载配置
    config_loaded = config.load_api_config(args.config)
    
    # 如果命令行提供了密钥，直接使用
    if args.key:
        config.GEMINI_API_CONFIG = [{"key": args.key}]
        config_loaded = True
    
    if args.openai_key:
        config.OPENAI_API_CONFIG = [{"key": args.openai_key}]
        config_loaded = True
    
    # 根据选择的API类型检查密钥
    api_type = args.api
    
    # 初始化变量
    max_concurrency = 0
    
    if api_type == "gemini" or api_type == "mixed":
        # 检查Gemini API密钥
        if not config_loaded or not config.GEMINI_API_CONFIG:
            logger.error("未找到有效的Gemini API配置，请使用 --create-config 创建配置模板")
            if api_type == "gemini":
                return
            # 如果是混合模式，警告用户将只使用OpenAI
            if api_type == "mixed":
                logger.warning("未找到有效的Gemini API配置，混合模式将仅使用OpenAI API")
        else:
            # 创建Gemini密钥管理器
            gemini_key_manager = APIKeyManager(config.GEMINI_API_CONFIG, config.DEFAULT_MAX_RPM)
            gemini_concurrency = gemini_key_manager.get_max_concurrency()
            max_concurrency = gemini_concurrency
            
            # 输出API密钥和RPM信息
            logger.info(f"共加载了 {len(config.GEMINI_API_CONFIG)} 个Gemini API密钥")
            
            # 打印每个密钥的RPM值
            for i, api_conf in enumerate(config.GEMINI_API_CONFIG):
                key_id = api_conf.get('key', '未指定')
                rpm = api_conf.get('rpm', config.DEFAULT_KEY_RPM)
                # 仅显示密钥的前6位和后4位，保护隐私
                masked_key = key_id[:6] + "..." + key_id[-4:] if len(key_id) > 10 else key_id
                logger.info(f"  密钥 {i+1}: {masked_key}, RPM={rpm}")
    
    if api_type == "openai" or api_type == "mixed":
        # 检查OpenAI API密钥
        if not config_loaded or not config.OPENAI_API_CONFIG:
            logger.error("未找到有效的OpenAI API配置，请使用 --create-config 创建配置模板")
            if api_type == "openai":
                return
            # 如果是混合模式，警告用户将只使用Gemini
            if api_type == "mixed" and gemini_key_manager is not None:
                logger.warning("未找到有效的OpenAI API配置，混合模式将仅使用Gemini API")
            elif api_type == "mixed":
                logger.error("未找到有效的Gemini和OpenAI API配置，请先配置API密钥")
                return
        else:
            # 创建OpenAI密钥管理器
            openai_key_manager = APIKeyManager(config.OPENAI_API_CONFIG, config.DEFAULT_MAX_RPM)
            openai_concurrency = openai_key_manager.get_max_concurrency()
            
            # 更新max_concurrency，如果是混合模式，取两者的总和
            if api_type == "mixed" and gemini_key_manager is not None:
                max_concurrency = gemini_concurrency + openai_concurrency
                logger.info(f"混合模式并发上限: Gemini={gemini_concurrency}, OpenAI={openai_concurrency}, 总计={max_concurrency}")
            else:
                max_concurrency = openai_concurrency
            
            # 输出API密钥和RPM信息
            logger.info(f"共加载了 {len(config.OPENAI_API_CONFIG)} 个OpenAI API密钥")
            
            # 打印每个密钥的RPM值
            for i, api_conf in enumerate(config.OPENAI_API_CONFIG):
                key_id = api_conf.get('key', '未指定')
                rpm = api_conf.get('rpm', config.DEFAULT_KEY_RPM)
                # 仅显示密钥的前6位和后4位，保护隐私
                masked_key = key_id[:6] + "..." + key_id[-4:] if len(key_id) > 10 else key_id
                logger.info(f"  密钥 {i+1}: {masked_key}, RPM={rpm}")
    
    # 确定最大工作线程数
    if args.max_workers:
        max_workers = args.max_workers
        logger.info(f"使用命令行指定的工作线程数: {max_workers}")
    else:
        # 直接使用密钥管理器提供的安全并发值
        max_workers = max_concurrency
        
        # 确保至少为1
        max_workers = max(1, max_workers)
        logger.info(f"使用API密钥管理器计算的安全并发值: {max_workers}")
    
    if api_type == "mixed":
        logger.info(f"混合模式: 同时使用Gemini和OpenAI API，并发上限={max_concurrency}")
    else:
        logger.info(f"{api_type.capitalize()} API密钥计算的并发上限: {max_concurrency}")
    
    logger.info(f"最终工作线程数设置为: {max_workers}")
    
    # 如果并发数为1，输出警告
    if max_workers == 1:
        logger.warning("注意: 当前工作线程数为1，将使用单线程处理。如需提高处理速度，可以:")
        logger.warning("1. 增加API密钥数量")
        logger.warning("2. 提高API密钥的RPM值")
        logger.warning("3. 使用--max-workers参数手动指定更高的并发数")
    
    # 确保提供了输入参数
    if not args.input and not args.pattern:
        logger.error("请指定输入文件路径或文件匹配模式")
        parser.print_help()
        return
    
    # 确定输入文件列表
    files_to_process = []
    
    if args.input:
        input_path = args.input
        if os.path.isfile(input_path):
            # 单个文件处理
            files_to_process = [input_path]
            # 默认输出目录：文件所在目录下的 "[文件名]_脱水" 目录
            if not args.output:
                file_dir = os.path.dirname(input_path) or "."
                file_base = os.path.splitext(os.path.basename(input_path))[0]
                OUTPUT_DIR = os.path.join(file_dir, f"{file_base}_脱水")
        elif os.path.isdir(input_path):
            # 目录处理
            if args.pattern:
                # 使用模式查找文件
                file_pattern = args.pattern
                num_range = None
                if args.range:
                    try:
                        start, end = map(int, args.range.split("-"))
                        num_range = (start, end)
                    except ValueError:
                        logger.error(f"范围格式错误: {args.range}，应为'start-end'")
                        return
                
                # 查找匹配的文件
                files_to_process = find_matching_files(
                    os.path.join(input_path, file_pattern),
                    num_range,
                    args.debug
                )
            else:
                # 处理目录下所有TXT文件
                for root, _, files in os.walk(input_path):
                    for file in files:
                        if file.endswith(".txt"):
                            files_to_process.append(os.path.join(root, file))
                
                # 按文件名排序
                files_to_process.sort()
            
            # 默认输出目录：输入目录下的 "[目录名]_脱水" 目录
            if not args.output:
                dir_name = os.path.basename(input_path.rstrip("/\\"))
                OUTPUT_DIR = os.path.join(input_path, f"{dir_name}_脱水")
        else:
            logger.error(f"输入路径不存在: {input_path}")
            return
    else:
        # 仅指定了模式，在当前目录下查找
        file_pattern = args.pattern
        num_range = None
        if args.range:
            try:
                start, end = map(int, args.range.split("-"))
                num_range = (start, end)
            except ValueError:
                logger.error(f"范围格式错误: {args.range}，应为'start-end'")
                return
        
        # 查找匹配的文件
        files_to_process = find_matching_files(file_pattern, num_range, args.debug)
        
        # 默认输出目录：当前目录下的 "脱水_输出" 目录
        if not args.output:
            OUTPUT_DIR = "脱水_输出"
    
    # 如果指定了输出目录，使用指定的
    if args.output:
        OUTPUT_DIR = args.output
    
    # 确保输出目录存在
    if OUTPUT_DIR:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"输出目录: {OUTPUT_DIR}")
        
        # 同步到file_utils中的全局变量
        import sys
        if 'file_utils' in sys.modules:
            sys.modules['file_utils'].OUTPUT_DIR = OUTPUT_DIR
        elif 'novel_condenser.file_utils' in sys.modules:
            sys.modules['novel_condenser.file_utils'].OUTPUT_DIR = OUTPUT_DIR
    
    # 测试模式处理前5个文件
    if args.test:
        logger.info("测试模式: 只处理前5个文件")
        files_to_process = files_to_process[:5]
    
    # 开始处理
    if not files_to_process:
        logger.warning("没有找到符合条件的文件")
        return
    
    statistics["total_files"] = len(files_to_process)
    logger.info(f"找到 {len(files_to_process)} 个文件待处理")
    
    # 选择处理模式
    if args.test:
        # 测试模式
        logger.info("启用测试模式，只处理前5个文件")
        if len(files_to_process) > 5:
            files_to_process = files_to_process[:5]
            
        # 使用顺序处理模式
        success_count, failed_files = process_files_sequentially(
            files_to_process, 
            len(files_to_process), 
            api_type=args.api,
            force_regenerate=args.force
        )
    elif args.sequential or max_workers == 1:
        # 顺序处理模式
        logger.info("使用顺序处理模式")
        success_count, failed_files = process_files_sequentially(
            files_to_process, 
            len(files_to_process), 
            api_type=args.api,
            force_regenerate=args.force
        )
    else:
        # 并发处理模式
        logger.info(f"使用并发处理模式，最大工作线程数: {max_workers}")
        success_count, failed_files = process_files_concurrently(
            files_to_process, 
            max_workers, 
            api_type=args.api,
            force_regenerate=args.force
        )
    
    # 完成统计
    finalize_statistics()
    
    # 输出处理摘要
    print_processing_summary(failed_files)

if __name__ == "__main__":
    main() 