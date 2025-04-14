#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API密钥管理模块 - 管理API密钥的分配和使用频率
"""

import time
import threading
from collections import deque
from typing import Dict, List, Optional

import config
from utils import setup_logger

logger = setup_logger(__name__)

# 定义默认常量
DEFAULT_KEY_RPM = 5  # 默认每个API密钥每分钟请求数
DEFAULT_MAX_RPM = 20  # 默认全局最大每分钟请求数

class APIKeyManager:
    """API密钥管理器：管理多个API密钥的分配和使用状态，并控制请求频率"""
    
    def __init__(self, api_configs: List[Dict], max_rpm: int = DEFAULT_MAX_RPM):
        """初始化密钥管理器

        Args:
            api_configs: API配置列表，每个配置包含key、redirect_url、model和rpm
            max_rpm: 全局最大每分钟请求数
        """
        self.api_configs = api_configs
        self.max_rpm = max_rpm
        
        # 为每个密钥添加默认rpm值
        for config in self.api_configs:
            if "rpm" not in config or not config["rpm"]:
                config["rpm"] = DEFAULT_KEY_RPM
        
        # 初始化密钥使用追踪
        self.key_usage = {config['key']: 0 for config in api_configs}
        
        # 用于RPM控制的请求时间队列（每个密钥维护一个最近请求时间队列）
        self.request_timestamps = {config['key']: deque(maxlen=max(config.get('rpm', DEFAULT_KEY_RPM), 
                                                            DEFAULT_KEY_RPM)) 
                                  for config in api_configs}
        
        # 全局请求时间队列
        self.global_request_timestamps = deque(maxlen=max_rpm)
        
        # 每个密钥的最大RPM限制
        self.max_key_rpm = max(config.get('rpm', DEFAULT_KEY_RPM) for config in api_configs) if api_configs else DEFAULT_KEY_RPM
        
        # 密钥错误计数和冷却时间
        self.key_errors = {config['key']: 0 for config in api_configs}
        self.key_cooldowns = {config['key']: 0 for config in api_configs}
        
        # 标记本次脱水中应该跳过的密钥
        self.skipped_keys = set()
        
        self.lock = threading.Lock()
    
    def get_key_config(self, timeout_sec: int = 30) -> Optional[Dict]:
        """获取可用的API密钥配置，如果所有密钥都忙则等待
        
        Args:
            timeout_sec: 最大等待时间(秒)，超过此时间仍无可用密钥则返回None
        
        Returns:
            Dict or None: API密钥配置字典或者None（如果没有可用的密钥）
        """
        # 最大等待次数计算
        max_wait_attempts = timeout_sec * 2  # 每0.5秒检查一次
        wait_attempts = 0
        backoff_count = 0  # 用于指数退避
        
        start_time = time.time()
        
        while wait_attempts < max_wait_attempts:
            need_to_wait = True  # 标记是否需要等待
            selected_key_config = None
            
            with self.lock:
                current_time = time.time()
                
                # 检查是否所有密钥都已被跳过
                valid_keys = [config['key'] for config in self.api_configs if config['key'] not in self.skipped_keys]
                if not valid_keys:
                    logger.warning("所有API密钥都已因错误次数过多而被跳过，脱水过程结束")
                    return None
                
                # 清理过期的请求记录和冷却时间
                self._clean_expired_requests(self.global_request_timestamps)
                self._update_key_cooldowns(current_time)
                
                # 检查全局RPM限制
                if len(self.global_request_timestamps) >= self.max_rpm:
                    # 全局请求限制逻辑
                    need_to_wait = True
                    if wait_attempts == 0:  # 只在第一次打印
                        logger.info(f"当前全局API请求已达到并发上限({self.max_rpm})，等待中...")
                else:
                    # 找到当前可用且负载最低的密钥
                    available_keys = []
                    
                    for config in self.api_configs:
                        # 获取密钥
                        key_id = config.get('key')
                        
                        # 跳过已标记的密钥
                        if key_id in self.skipped_keys:
                            continue
                        
                        # 跳过处于冷却期的密钥
                        if self.key_cooldowns.get(key_id, 0) > current_time:
                            continue
                        
                        # 清理该密钥的过期请求
                        if key_id in self.request_timestamps:
                            self._clean_expired_requests(self.request_timestamps[key_id])
                        
                        # 获取该密钥的RPM限制
                        key_max_rpm = config.get('rpm', DEFAULT_KEY_RPM)
                        
                        # 检查该密钥的当前RPM
                        key_rpm = len(self.request_timestamps.get(key_id, []))
                        if key_rpm < key_max_rpm:
                            # 计算该密钥当前的负载率
                            load_ratio = key_rpm / key_max_rpm if key_max_rpm > 0 else 0
                            available_keys.append((key_id, load_ratio, config))
                    
                    # 如果没有可用密钥，设置等待标志
                    if not available_keys:
                        need_to_wait = True
                        if wait_attempts == 0:  # 只在第一次打印
                            logger.info("当前所有API密钥都已达到并发上限或处于冷却期，等待中...")
                    else:
                        # 找到负载率最低的密钥
                        selected_key_info = min(available_keys, key=lambda x: x[1])
                        selected_key_id = selected_key_info[0]
                        selected_key_config = selected_key_info[2]
                        
                        # 更新请求记录
                        if selected_key_id not in self.request_timestamps:
                            max_len = selected_key_config.get('rpm', DEFAULT_KEY_RPM)
                            self.request_timestamps[selected_key_id] = deque(maxlen=max_len)
                        
                        self.request_timestamps[selected_key_id].append(current_time)
                        self.global_request_timestamps.append(current_time)
                        
                        # 已找到配置，不需要等待
                        need_to_wait = False
            
            # 在锁外处理结果
            
            # 如果找到配置，返回
            if not need_to_wait and selected_key_config:
                elapsed = time.time() - start_time
                if wait_attempts > 0:  # 如果之前有等待
                    logger.info(f"已获取可用API密钥，等待了{elapsed:.2f}秒")
                
                # 返回密钥配置的副本，避免外部修改
                return selected_key_config.copy()
            
            # 检查是否超时
            if time.time() - start_time > timeout_sec:
                logger.warning(f"等待可用API密钥超时 ({timeout_sec}秒)，放弃处理...")
                return None
            
            # 需要等待的情况
            wait_attempts += 1
            
            # 使用指数退避策略计算等待时间（最大5秒）
            wait_time = min(0.5 * (2 ** backoff_count), 5.0)
            
            # 每3次尝试增加退避计数
            if wait_attempts % 3 == 0:
                backoff_count += 1
            
            time.sleep(wait_time)
        
        # 超过最大等待次数，最终返回None
        logger.warning("等待可用API密钥超时，放弃处理...")
        return None
    
    def _clean_expired_requests(self, timestamp_queue: deque) -> None:
        """清理超过一分钟的请求记录

        Args:
            timestamp_queue: 时间戳队列
        """
        current_time = time.time()
        while timestamp_queue and current_time - timestamp_queue[0] > 60:
            timestamp_queue.popleft()
    
    def _update_key_cooldowns(self, current_time: float) -> None:
        """更新密钥冷却时间，移除已过期的冷却期

        Args:
            current_time: 当前时间戳
        """
        for key in list(self.key_cooldowns.keys()):
            if self.key_cooldowns[key] <= current_time:
                self.key_cooldowns[key] = 0
    
    def report_error(self, key: str, error_type: str = "general") -> None:
        """报告密钥使用中的错误，根据错误次数可能会暂时禁用该密钥

        Args:
            key: API密钥
            error_type: 错误类型，可用于区分不同错误的处理方式
        """
        with self.lock:
            if key not in self.key_errors:
                return
                
            self.key_errors[key] += 1
            error_count = self.key_errors[key]
            
            # 根据错误类型和次数设置不同的冷却时间
            cooldown_time = 0
            
            # 当错误次数超过20次时，将该密钥标记为在本次脱水中跳过，而不是设置长时间冷却
            if error_count >= 20:
                self.skipped_keys.add(key)
                logger.warning(f"密钥 {key[:8]}... 失败次数已达到{error_count}次（超过20次），本次脱水跳过此密钥")
                
                # 检查是否所有密钥都已被跳过
                valid_keys = [config['key'] for config in self.api_configs if config['key'] not in self.skipped_keys]
                if not valid_keys:
                    logger.warning("所有API密钥都已因错误次数过多而被跳过，脱水过程将结束")
            elif error_type == "rate_limit":  # API速率限制错误
                cooldown_time = min(60 * (2 ** min(error_count-1, 4)), 3600)  # 最长1小时冷却
                logger.warning(f"密钥 {key[:8]}... 触发速率限制，设置冷却 {cooldown_time} 秒")
            elif error_type == "invalid_key":  # 无效密钥错误
                cooldown_time = 3600  # 设置1小时冷却
                logger.error(f"密钥 {key[:8]}... 无效，暂时禁用1小时")
            else:  # 一般错误
                if error_count >= 5:  # 连续5次错误
                    cooldown_time = min(30 * (2 ** min(error_count-5, 4)), 1800)  # 最长30分钟冷却
                    logger.warning(f"密钥 {key[:8]}... 连续 {error_count} 次错误，设置冷却 {cooldown_time} 秒")
            
            if cooldown_time > 0:
                self.key_cooldowns[key] = time.time() + cooldown_time
    
    def report_success(self, key: str) -> None:
        """报告密钥使用成功，重置错误计数

        Args:
            key: API密钥
        """
        with self.lock:
            if key in self.key_errors:
                self.key_errors[key] = 0
    
    def get_max_concurrency(self) -> int:
        """获取基于可用密钥和RPM限制的最大并发数
        
        Returns:
            int: 最大可能的并发数
        """
        if not self.api_configs:
            return 1
            
        # 计算所有API密钥的RPM总和
        total_rpm = sum(config.get('rpm', DEFAULT_KEY_RPM) for config in self.api_configs)
        
        # 计算基于密钥数量和RPM的并发数
        if len(self.api_configs) == 1:
            # 单个密钥时的计算逻辑：每5个RPM支持1个并发
            rpm_based_concurrency = max(1, int(total_rpm / 5))
        else:
            # 多个密钥时的计算逻辑：每10个RPM支持1个并发，但至少有密钥数量一半的并发数
            rpm_based = max(1, int(total_rpm / 10))
            key_count_based = max(1, len(self.api_configs) // 2)
            rpm_based_concurrency = max(rpm_based, key_count_based)
        
        # 与全局RPM限制比较，取较小值
        concurrency = min(rpm_based_concurrency, self.max_rpm)
        
        # 如果密钥数量大于5，增加最大并发上限
        if len(self.api_configs) > 5:
            return min(max(concurrency, len(self.api_configs)), 20)
        else:
            return min(concurrency, 10)
    
    def get_healthy_key_count(self) -> int:
        """获取当前健康（不在冷却期）的密钥数量
        
        Returns:
            int: 健康密钥数量
        """
        current_time = time.time()
        with self.lock:
            return sum(1 for key, cooldown in self.key_cooldowns.items() 
                      if cooldown <= current_time)
    
    def reset_cooldowns(self) -> None:
        """重置所有密钥的冷却时间和错误计数，用于手动恢复所有密钥
        """
        with self.lock:
            for key in self.key_cooldowns:
                self.key_cooldowns[key] = 0
                self.key_errors[key] = 0
            
            # 清空跳过的密钥集合
            self.skipped_keys.clear()
            
            logger.info("已重置所有API密钥的冷却时间、错误计数和跳过标记") 