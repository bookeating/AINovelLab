#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API密钥管理模块 - 管理API密钥的分配和使用频率
"""

import time
import threading
from collections import deque
from typing import Dict, List, Optional

# 导入配置
try:
    from . import config
    from ..utils import setup_logger
except ImportError:
    import config
    from utils import setup_logger

# 设置日志记录器
logger = setup_logger(__name__)

class APIKeyManager:
    """API密钥管理器：管理多个API密钥的分配和使用状态，并控制请求频率"""
    
    def __init__(self, api_configs: List[Dict], max_rpm: int = config.DEFAULT_MAX_RPM):
        """初始化密钥管理器

        Args:
            api_configs: API配置列表，每个配置包含key、redirect_url、model和rpm
            max_rpm: 全局最大每分钟请求数
        """
        self.api_configs = api_configs
        self.max_rpm = max_rpm
        
        # 为每个密钥添加默认rpm值和错误计数
        for api_config in self.api_configs:
            if "rpm" not in api_config or not api_config["rpm"]:
                api_config["rpm"] = config.DEFAULT_KEY_RPM
            api_config["errors"] = 0  # 初始化错误计数
            api_config["consecutive_errors"] = 0  # 连续错误计数
            api_config["cooling_until"] = 0  # 冷却期截止时间
        
        # 初始化密钥使用追踪
        self.key_usage = {api_config['key']: 0 for api_config in api_configs}
        
        # 用于RPM控制的请求时间队列（每个密钥维护一个最近请求时间队列）
        self.request_timestamps = {api_config['key']: deque(maxlen=max(api_config['rpm'], config.DEFAULT_KEY_RPM)) 
                                  for api_config in api_configs}
        
        # 每个密钥的请求成功率
        self.success_rates = {api_config['key']: 1.0 for api_config in api_configs}  # 初始成功率为100%
        
        # 全局请求时间队列
        self.global_request_timestamps = deque(maxlen=max_rpm)
        
        # 每个密钥的最大RPM限制
        self.max_key_rpm = max(api_config.get('rpm', config.DEFAULT_KEY_RPM) for api_config in api_configs) if api_configs else config.DEFAULT_KEY_RPM
        
        # 密钥轮换索引 - 用于实现简单的轮询策略
        self.next_key_index = 0
        
        # 标记本次脱水中应该跳过的密钥
        self.skipped_keys = set()
        
        self.lock = threading.Lock()
        
        # 打印初始化信息
        logger.info(f"已初始化API密钥管理器，共{len(api_configs)}个密钥，全局RPM上限:{max_rpm}")
    
    def get_key_config(self):
        """获取可用的API密钥配置
        
        使用更智能的密钥选择策略，考虑密钥的负载均衡、成功率和错误历史
        
        Returns:
            API密钥配置字典或者None（如果没有可用的密钥）
        """
        # 最大等待次数（60次 * 0.5秒 = 最多等待30秒）
        max_wait_attempts = 60
        wait_attempts = 0
        backoff_count = 0  # 用于指数退避
        
        while wait_attempts < max_wait_attempts:
            need_to_wait = True  # 标记是否需要等待
            selected_key_config = None
            
            with self.lock:
                current_time = time.time()
                
                # 清理过期的请求记录
                self._clean_expired_requests(self.global_request_timestamps)
                
                # 检查全局RPM限制
                if len(self.global_request_timestamps) >= self.max_rpm:
                    # 全局请求限制逻辑
                    need_to_wait = True
                    if wait_attempts == 0:  # 只在第一次打印
                        logger.debug(f"当前全局API请求已达到并发上限({self.max_rpm})，等待中...")
                else:
                    # 找到当前可用且最优的密钥
                    available_keys = []
                    
                    for i, api_config in enumerate(self.api_configs):
                        # 获取密钥
                        key_id = api_config.get('key')
                        
                        # 检查密钥是否在冷却期
                        if api_config.get("cooling_until", 0) > current_time:
                            continue
                        
                        # 检查是否在跳过列表中
                        if key_id in self.skipped_keys:
                            continue
                            
                        # 清理该密钥的过期请求
                        if key_id in self.request_timestamps:
                            self._clean_expired_requests(self.request_timestamps[key_id])
                        
                        # 检查该密钥的RPM限制
                        key_rpm = len(self.request_timestamps.get(key_id, []))
                        max_key_rpm = api_config.get('rpm', config.DEFAULT_KEY_RPM)
                        
                        if key_rpm < max_key_rpm:
                            # 计算该密钥当前的负载率和得分
                            # 得分考虑三个因素：负载率、成功率、索引(为了轮询)
                            load_ratio = key_rpm / max_key_rpm if max_key_rpm > 0 else 0
                            success_rate = self.success_rates.get(key_id, 0.5)  # 默认50%成功率
                            
                            # 轮询权重 - 根据索引距离计算，越早轮到的索引得分越高
                            rotation_weight = 1.0 - (((i - self.next_key_index) % len(self.api_configs)) / len(self.api_configs))
                            
                            # 总分 = 成功率(50%) - 负载率(30%) + 轮询权重(20%)
                            score = (success_rate * 0.5) - (load_ratio * 0.3) + (rotation_weight * 0.2)
                            
                            available_keys.append((key_id, score, api_config, i))
                    
                    # 如果没有可用密钥，设置等待标志
                    if not available_keys:
                        need_to_wait = True
                        if wait_attempts == 0:  # 只在第一次打印
                            logger.debug("当前所有API密钥都已达到并发上限或在冷却期，等待中...")
                    else:
                        # 找到得分最高的密钥
                        selected_key_info = max(available_keys, key=lambda x: x[1])
                        selected_key_id = selected_key_info[0]
                        selected_key_config = selected_key_info[2]
                        selected_index = selected_key_info[3]
                        
                        # 更新下一个密钥索引，实现轮询
                        self.next_key_index = (selected_index + 1) % len(self.api_configs)
                        
                        # 更新请求记录
                        if selected_key_id not in self.request_timestamps:
                            self.request_timestamps[selected_key_id] = deque(maxlen=self.max_key_rpm)
                        
                        self.request_timestamps[selected_key_id].append(current_time)
                        self.global_request_timestamps.append(current_time)
                        
                        # 已找到配置，不需要等待
                        need_to_wait = False
            
            # 在锁外处理结果
            
            # 如果找到配置，返回
            if not need_to_wait and selected_key_config:
                if wait_attempts > 0:  # 如果之前有等待
                    logger.debug(f"已获取可用API密钥，继续处理...")
                return selected_key_config.copy()
            
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
        # 删除所有超过60秒的记录
        while timestamp_queue and current_time - timestamp_queue[0] > 60:
            timestamp_queue.popleft()
    
    def release_key(self, key: str) -> None:
        """释放API密钥的使用

        Args:
            key: 要释放的API密钥
        """
        with self.lock:
            if isinstance(key, dict):
                # 如果传入的是配置字典，则提取key值
                key = key.get('key')
            
            if key in self.key_usage:
                self.key_usage[key] = max(0, self.key_usage[key] - 1)
    
    def report_success(self, key: str) -> None:
        """报告API密钥请求成功
        
        Args:
            key: API密钥
        """
        if isinstance(key, dict):
            key = key.get('key')
        
        with self.lock:
            # 更新成功率 (使用EMA-指数移动平均)
            current_rate = self.success_rates.get(key, 0.5)
            self.success_rates[key] = current_rate * 0.9 + 0.1  # 成功=1.0
            
            # 重置连续错误计数
            for api_config in self.api_configs:
                if api_config.get('key') == key:
                    api_config["consecutive_errors"] = 0
                    break
    
    def report_error(self, key: str) -> None:
        """报告API密钥请求失败
        
        Args:
            key: API密钥或配置字典
        """
        if isinstance(key, dict):
            key = key.get('key')
        
        with self.lock:
            # 更新成功率 (使用EMA-指数移动平均)
            current_rate = self.success_rates.get(key, 0.5)
            self.success_rates[key] = current_rate * 0.9  # 失败=0.0
            
            # 更新错误计数
            for api_config in self.api_configs:
                if api_config.get('key') == key:
                    api_config["errors"] = api_config.get("errors", 0) + 1
                    api_config["consecutive_errors"] = api_config.get("consecutive_errors", 0) + 1
                    
                    # 如果连续错误超过阈值，设置冷却期
                    if api_config["consecutive_errors"] >= 3:
                        # 指数冷却，随着连续错误次数增加冷却时间
                        cooling_time = min(30 * (2 ** (api_config["consecutive_errors"] - 3)), 600)  # 最长10分钟
                        api_config["cooling_until"] = time.time() + cooling_time
                        logger.warning(f"密钥连续失败{api_config['consecutive_errors']}次，进入冷却期{cooling_time}秒")
                    
                    # 如果总错误次数过多，加入跳过列表
                    if api_config["errors"] >= 20:
                        self.skipped_keys.add(key)
                        logger.warning(f"密钥错误次数过多({api_config['errors']}次)，本次脱水将跳过此密钥")
                        
                        # 检查是否所有密钥都被跳过
                        valid_keys = [c.get('key') for c in self.api_configs 
                                    if c.get('key') not in self.skipped_keys]
                        if not valid_keys:
                            logger.warning("所有API密钥都已因错误次数过多而被跳过，脱水过程将结束")
                    break
    
    def get_max_concurrency(self) -> int:
        """获取支持的最大并发数

        基于API密钥的数量和RPM限制计算最大并发数

        Returns:
            最大并发数
        """
        if not self.api_configs:
            return 1
        
        # 计算所有API密钥的RPM总和
        total_rpm = sum(api_config.get('rpm', config.DEFAULT_KEY_RPM) for api_config in self.api_configs)
        
        # 自由版API每分钟限制值（每个密钥RPM不能超过这个值）
        free_tier_limit = 15
        
        # 考虑每个密钥的实际限制
        adjusted_rpm = 0
        for api_config in self.api_configs:
            # 获取密钥的RPM设置
            key_rpm = api_config.get('rpm', config.DEFAULT_KEY_RPM)
            # 应用自由版限制
            actual_rpm = min(key_rpm, free_tier_limit)
            adjusted_rpm += actual_rpm
        
        # 修改并发度计算逻辑，使小RPM值也能获得合理的并发度：
        # 1. 对于单个密钥，每10个RPM支持1个并发（降低门槛）
        # 2. 对于多个密钥，使用更积极的计算公式
        
        if len(self.api_configs) == 1:
            # 单个密钥时的计算逻辑：每10个RPM支持1个并发
            safest_concurrency = max(1, int(adjusted_rpm / 5))
        else:
            # 多个密钥时的计算逻辑：更积极地计算并发数
            safest_concurrency = max(1, int(adjusted_rpm / 30))
        
        # 确保至少返回1，最大返回10
        return min(safest_concurrency, 10) 