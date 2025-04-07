#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API服务模块 - 处理Gemini API和OpenAI API的调用和响应
"""

import json
import requests
import time
import traceback
from typing import Dict, Optional, List, Any, Union

# 导入配置和工具
try:
    from . import config
    from .key_manager import APIKeyManager
    from ..utils import setup_logger
except ImportError:
    import config
    from key_manager import APIKeyManager
    from utils import setup_logger

# 设置日志记录器
logger = setup_logger(__name__)

# 尝试导入全局gemini_key_manager
try:
    from . import main
    global_key_manager = main.gemini_key_manager
except (ImportError, AttributeError):
    global_key_manager = None

# 尝试导入全局openai_key_manager
try:
    from . import main
    global_openai_key_manager = main.openai_key_manager
except (ImportError, AttributeError):
    global_openai_key_manager = None

def condense_novel_gemini(content: str, api_key_config: Optional[Dict] = None, key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """使用Gemini API对小说内容进行压缩处理
    
    Args:
        content: 小说内容
        api_key_config: API密钥配置
        key_manager: API密钥管理器实例

    Returns:
        Optional[str]: 压缩后的内容，处理失败则返回None
    """
    # 如果内容为空，直接返回空字符串
    if not content or len(content.strip()) == 0:
        logger.warning("输入内容为空，无法处理")
        return ""
    
    # 获取API密钥配置
    if api_key_config is None:
        # 优先使用传入的key_manager
        if key_manager is None:
            # 尝试使用全局key_manager
            if global_key_manager is not None:
                key_manager = global_key_manager
                logger.debug("使用全局API密钥管理器")
            else:
                # 尝试动态导入main模块中的key_manager（避免循环导入问题）
                try:
                    # 仅当直接运行此模块时才需要这样导入
                    import sys
                    if 'main' in sys.modules:
                        main_module = sys.modules['main']
                        if hasattr(main_module, 'gemini_key_manager') and main_module.gemini_key_manager is not None:
                            key_manager = main_module.gemini_key_manager
                            logger.debug("从main模块动态获取到API密钥管理器")
                        else:
                            logger.debug("main模块中未找到gemini_key_manager")
                    elif 'novel_condenser.main' in sys.modules:
                        main_module = sys.modules['novel_condenser.main']
                        if hasattr(main_module, 'gemini_key_manager') and main_module.gemini_key_manager is not None:
                            key_manager = main_module.gemini_key_manager
                            logger.debug("从novel_condenser.main模块动态获取到API密钥管理器")
                        else:
                            logger.debug("novel_condenser.main模块中未找到gemini_key_manager")
                except Exception as e:
                    logger.debug(f"尝试动态获取key_manager时出错: {e}")
                
                # 只有在没有其他选择时才创建新的APIKeyManager
                if key_manager is None:
                    logger.warning("未找到现有的API密钥管理器，创建临时管理器")
                    key_manager = APIKeyManager(config.GEMINI_API_CONFIG, config.DEFAULT_MAX_RPM)
        
        # 从key_manager获取API密钥配置
        api_key_config = key_manager.get_key_config()
        
        if api_key_config is None:
            # 检查是否因为所有密钥都被跳过而无法获取密钥
            if key_manager and hasattr(key_manager, 'skipped_keys'):
                valid_keys = [api_conf['key'] for api_conf in key_manager.api_configs 
                             if api_conf['key'] not in key_manager.skipped_keys]
                if not valid_keys:
                    logger.error("所有API密钥都因失败次数过多被跳过，脱水过程结束")
                    return None
                
            logger.error("无法获取可用的API密钥，请检查配置或等待密钥冷却期结束")
            return None
    
    api_key = api_key_config.get('key')
    redirect_url = api_key_config.get('redirect_url')
    model = api_key_config.get('model', config.DEFAULT_GEMINI_MODEL)
    
    # 计算内容长度，超长的内容需要分段处理
    content_length = len(content)
    max_chunk_length = 20000  # 单次处理的最大字符数
    
    # 如果内容长度小于阈值，则直接处理
    if content_length <= max_chunk_length:
        return _process_content_with_gemini(content, api_key, redirect_url, model)
    
    # 否则分段处理
    logger.debug(f"内容长度为 {content_length} 字符，将分段处理...")
    
    # 分段计算
    chunk_size = max_chunk_length
    total_chunks = (content_length + chunk_size - 1) // chunk_size
    logger.debug(f"将分为 {total_chunks} 段进行处理")
    
    # 存储各段的处理结果
    condensed_chunks = []
    
    # 分段处理
    for i in range(total_chunks):
        start_pos = i * chunk_size
        end_pos = min(start_pos + chunk_size, content_length)
        chunk = content[start_pos:end_pos]
        
        logger.debug(f"处理第 {i+1}/{total_chunks} 段，字符范围: {start_pos}-{end_pos}...")
        
        # 处理当前段
        condensed_chunk = _process_content_with_gemini(
            chunk, api_key, redirect_url, model, 
            is_chunk=True, chunk_index=i+1, total_chunks=total_chunks
        )
        
        if condensed_chunk is None:
            # 如果有一段处理失败，则尝试获取新的API密钥
            logger.warning(f"第 {i+1} 段处理失败，尝试获取新的API密钥...")
            
            if key_manager:
                # 报告当前密钥错误
                key_manager.report_error(api_key)
                
                # 获取新的API密钥
                api_key_config = key_manager.get_key_config()
                if api_key_config:
                    api_key = api_key_config.get('key')
                    redirect_url = api_key_config.get('redirect_url')
                    model = api_key_config.get('model', config.DEFAULT_GEMINI_MODEL)
                    
                    # 重试当前段
                    logger.debug(f"使用新的API密钥重试第 {i+1} 段...")
                    condensed_chunk = _process_content_with_gemini(
                        chunk, api_key, redirect_url, model, 
                        is_chunk=True, chunk_index=i+1, total_chunks=total_chunks
                    )
        
        if condensed_chunk is None:
            logger.error(f"第 {i+1} 段处理失败，已尝试所有可用的API密钥")
            return None
        
        condensed_chunks.append(condensed_chunk)
    
    # 合并处理结果
    condensed_content = "\n\n".join(condensed_chunks)
    
    if key_manager:
        # 报告成功
        key_manager.report_success(api_key)
        
    return condensed_content

def _process_content_with_gemini(content: str, api_key: str, redirect_url: str, model: str, 
                               is_chunk: bool = False, chunk_index: int = 0, total_chunks: int = 0) -> Optional[str]:
    """使用Gemini API处理单个内容块
    
    Args:
        content: 要处理的内容
        api_key: API密钥
        redirect_url: API端点URL
        model: 模型名称
        is_chunk: 是否为分块处理的一部分
        chunk_index: 分块索引
        total_chunks: 总分块数
    
    Returns:
        Optional[str]: 处理后的内容，处理失败则返回None
    """
    # 构建提示词
    prefix = ""
    if is_chunk:
        prefix = f"这是一个小说的第{chunk_index}段，共{total_chunks}段。"
    
    system_prompt = f"{prefix}你是一个小说内容压缩工具。请将下面的小说内容精简到原来的30%-50%左右，同时保留所有重要情节、对话和描写，不要遗漏关键情节和人物。不要添加任何解释或总结，直接输出压缩后的内容。"
    
    # 构建正确的API URL格式
    # 不同API服务商可能有不同的URL格式
    final_api_url = ""
    
    # 针对官方Google API的正规URL格式
    if redirect_url and "generativelanguage.googleapis.com" in redirect_url:
        # 官方格式: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_API_KEY
        if ":generateContent" in redirect_url:
            # 完整URL已提供
            final_api_url = redirect_url
        else:
            # 只提供了基础URL，需要添加模型和方法
            if redirect_url.endswith('/'):
                final_api_url = f"{redirect_url}{model}:generateContent"
            else:
                final_api_url = f"{redirect_url}/{model}:generateContent"
        
        # 添加API密钥参数
        if "key=" not in final_api_url:
            if "?" in final_api_url:
                final_api_url += f"&key={api_key}"
            else:
                final_api_url += f"?key={api_key}"
    
    # 针对第三方API服务商的URL格式
    elif redirect_url and "aliyahzombie" in redirect_url:
        # 第三方服务可能有特殊格式
        if ":generateContent" in redirect_url:
            final_api_url = redirect_url
        else:
            if redirect_url.endswith('/'):
                final_api_url = f"{redirect_url}{model}:generateContent"
            else:
                final_api_url = f"{redirect_url}/{model}:generateContent"
        
        # 特殊认证处理 - 第三方API的具体认证方式
        headers_custom = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
    else:
        # 使用默认URL格式
        if not redirect_url:
            redirect_url = config.DEFAULT_GEMINI_API_URL
            
        if ":generateContent" in redirect_url:
            final_api_url = redirect_url
        else:
            if redirect_url.endswith('/'):
                final_api_url = f"{redirect_url}{model}:generateContent"
            else:
                final_api_url = f"{redirect_url}/{model}:generateContent"
        
        # 添加API密钥
        if "key=" not in final_api_url:
            if "?" in final_api_url:
                final_api_url += f"&key={api_key}"
            else:
                final_api_url += f"?key={api_key}"
    
    # 详细记录URL以便调试
    logger.debug(f"API请求URL: {final_api_url}")
    
    # 构建v1beta格式的请求体
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": system_prompt},
                    {"text": content}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topK": 40,
            "topP": 0.8,
            "maxOutputTokens": 8192,
            "responseMimeType": "text/plain",  # 明确要求返回纯文本
            "stopSequences": ["Thinking:"],    # 阻止思维链格式的输出
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]
    }
    
    # 构建请求头 
    headers = {
        "Content-Type": "application/json"
    }
    
    # 为不同API服务商设置不同的请求头
    if redirect_url and "aliyahzombie" in redirect_url:
        # 使用自定义标头
        headers = headers_custom
    elif "key=" not in final_api_url:
        # 如果URL中没有key参数，则在请求头中添加
        headers["x-goog-api-key"] = api_key
    
    # 添加重试逻辑
    max_retries = 3
    retry_delay = 5
    
    for retry in range(max_retries):
        try:
            # 发送请求
            logger.debug(f"发送API请求 (尝试 {retry+1}/{max_retries})")
            response = requests.post(final_api_url, headers=headers, json=request_data, timeout=120)
            
            # 检查响应状态码
            if response.status_code == 200:
                response_json = response.json()
                
                # 提取生成的文本
                if ("candidates" in response_json and
                    len(response_json["candidates"]) > 0 and
                    "content" in response_json["candidates"][0] and
                    "parts" in response_json["candidates"][0]["content"] and
                    len(response_json["candidates"][0]["content"]["parts"]) > 0):
                    
                    # 收集所有文本部分
                    collected_text = []
                    parts = response_json["candidates"][0]["content"]["parts"]
                    
                    for part in parts:
                        if "text" in part:
                            # 标准文本形式
                            collected_text.append(part["text"])
                        elif "thing" in part and "thinking" in part["thing"]:
                            # thing中可能包含thinking
                            collected_text.append(part["thing"]["thinking"])
                        elif "thing" in part and "value" in part["thing"]:
                            # 或者thing中包含value
                            collected_text.append(part["thing"]["value"])
                        elif "thing" in part and isinstance(part["thing"], str):
                            # 或者thing直接是字符串
                            collected_text.append(part["thing"])
                    
                    # 合并所有文本
                    condensed_text = "\n".join([text for text in collected_text if text.strip()])
                    
                    if condensed_text.strip():
                        # 成功获取到压缩后的内容
                        return condensed_text.strip()
                    else:
                        logger.warning("API返回了空内容")
                        # 尝试记录完整响应进行调试
                        logger.debug(f"完整响应: {json.dumps(response_json)}")
                
                # 响应格式不符合预期
                logger.error(f"API响应格式异常")
                logger.debug(f"异常响应详情: {json.dumps(response_json)}")
                
            else:
                # 记录详细的错误信息
                logger.error(f"API请求失败: HTTP {response.status_code}")
                try:
                    error_json = response.json()
                    logger.error(f"错误详情: {json.dumps(error_json)}")
                    if "error" in error_json and "message" in error_json["error"]:
                        logger.error(f"错误消息: {error_json['error']['message']}")
                        
                        # 处理HTTP 429 - 配额超限错误
                        if response.status_code == 429:
                            # 尝试从错误信息中获取建议的重试延迟时间
                            retry_delay_seconds = 60  # 默认等待60秒
                            
                            # 检查是否有RetryInfo
                            if "error" in error_json and "details" in error_json["error"]:
                                for detail in error_json["error"]["details"]:
                                    if "@type" in detail and detail["@type"] == "type.googleapis.com/google.rpc.RetryInfo":
                                        if "retryDelay" in detail:
                                            # 提取建议的延迟时间，例如"58s"
                                            delay_str = detail["retryDelay"]
                                            if isinstance(delay_str, str) and 's' in delay_str:
                                                try:
                                                    # 解析秒数，例如从"58s"中提取58
                                                    retry_delay_seconds = int(delay_str.replace('s', ''))
                                                    # 添加额外的缓冲时间
                                                    retry_delay_seconds += 5
                                                except ValueError:
                                                    pass
                            
                            logger.warning(f"API配额超限，将等待{retry_delay_seconds}秒后重试...")
                            time.sleep(retry_delay_seconds)
                            # 如果是最后一次重试，不要增加重试计数，直接再试一次
                            if retry == max_retries - 1:
                                retry -= 1
                            continue  # 跳过下面的重试逻辑，直接开始下一次循环
                except:
                    logger.error(f"响应内容: {response.text}")
            
            # 如果还有重试次数，则等待后重试
            if retry < max_retries - 1:
                sleep_time = retry_delay * (2 ** retry)
                logger.debug(f"将在 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error(f"已达到最大重试次数，处理失败")
                
        except requests.exceptions.Timeout:
            logger.warning("API请求超时")
            if retry < max_retries - 1:
                sleep_time = retry_delay * (2 ** retry)
                logger.debug(f"将在 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error("已达到最大重试次数，处理失败")
                
        except Exception as e:
            logger.error(f"请求处理过程中发生错误: {e}")
            logger.debug(traceback.format_exc())
            if retry < max_retries - 1:
                sleep_time = retry_delay * (2 ** retry)
                logger.debug(f"将在 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error("已达到最大重试次数，处理失败")
    
    # 所有重试都失败
    return None

def condense_novel_openai(content: str, api_key_config: Optional[Dict] = None, key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """使用OpenAI API对小说内容进行压缩处理
    
    Args:
        content: 小说内容
        api_key_config: API密钥配置
        key_manager: API密钥管理器实例

    Returns:
        Optional[str]: 压缩后的内容，处理失败则返回None
    """
    # 如果内容为空，直接返回空字符串
    if not content or len(content.strip()) == 0:
        logger.warning("输入内容为空，无法处理")
        return ""
    
    # 获取API密钥配置
    if api_key_config is None:
        # 优先使用传入的key_manager
        if key_manager is None:
            # 尝试使用全局key_manager
            if global_openai_key_manager is not None:
                key_manager = global_openai_key_manager
                logger.debug("使用全局OpenAI API密钥管理器")
            else:
                # 尝试动态导入main模块中的key_manager（避免循环导入问题）
                try:
                    # 仅当直接运行此模块时才需要这样导入
                    import sys
                    if 'main' in sys.modules:
                        main_module = sys.modules['main']
                        if hasattr(main_module, 'openai_key_manager') and main_module.openai_key_manager is not None:
                            key_manager = main_module.openai_key_manager
                            logger.debug("从main模块动态获取到OpenAI API密钥管理器")
                        else:
                            logger.debug("main模块中未找到openai_key_manager")
                    elif 'novel_condenser.main' in sys.modules:
                        main_module = sys.modules['novel_condenser.main']
                        if hasattr(main_module, 'openai_key_manager') and main_module.openai_key_manager is not None:
                            key_manager = main_module.openai_key_manager
                            logger.debug("从novel_condenser.main模块动态获取到OpenAI API密钥管理器")
                        else:
                            logger.debug("novel_condenser.main模块中未找到openai_key_manager")
                except Exception as e:
                    logger.debug(f"尝试动态获取OpenAI key_manager时出错: {e}")
                
                # 只有在没有其他选择时才创建新的APIKeyManager
                if key_manager is None:
                    logger.warning("未找到现有的OpenAI API密钥管理器，创建临时管理器")
                    key_manager = APIKeyManager(config.OPENAI_API_CONFIG, config.DEFAULT_MAX_RPM)
        
        # 从key_manager获取API密钥配置
        api_key_config = key_manager.get_key_config()
        
        if api_key_config is None:
            # 检查是否因为所有密钥都被跳过而无法获取密钥
            if key_manager and hasattr(key_manager, 'skipped_keys'):
                valid_keys = [api_conf['key'] for api_conf in key_manager.api_configs 
                             if api_conf['key'] not in key_manager.skipped_keys]
                if not valid_keys:
                    logger.error("所有OpenAI API密钥都因失败次数过多被跳过，脱水过程结束")
                    return None
                
            logger.error("无法获取可用的OpenAI API密钥，请检查配置或等待密钥冷却期结束")
            return None
    
    api_key = api_key_config.get('key')
    redirect_url = api_key_config.get('redirect_url')
    model = api_key_config.get('model', config.DEFAULT_OPENAI_MODEL)
    
    # 计算内容长度，超长的内容需要分段处理
    content_length = len(content)
    max_chunk_length = 20000  # 单次处理的最大字符数
    
    # 如果内容长度小于阈值，则直接处理
    if content_length <= max_chunk_length:
        return _process_content_with_openai(content, api_key, redirect_url, model)
    
    # 否则分段处理
    logger.debug(f"内容长度为 {content_length} 字符，将分段处理...")
    
    # 分段计算
    chunk_size = max_chunk_length
    total_chunks = (content_length + chunk_size - 1) // chunk_size
    logger.debug(f"将分为 {total_chunks} 段进行处理")
    
    # 存储各段的处理结果
    condensed_chunks = []
    
    # 分段处理
    for i in range(total_chunks):
        start_pos = i * chunk_size
        end_pos = min(start_pos + chunk_size, content_length)
        chunk = content[start_pos:end_pos]
        
        logger.debug(f"处理第 {i+1}/{total_chunks} 段，字符范围: {start_pos}-{end_pos}...")
        
        # 处理当前段
        condensed_chunk = _process_content_with_openai(
            chunk, api_key, redirect_url, model, 
            is_chunk=True, chunk_index=i+1, total_chunks=total_chunks
        )
        
        if condensed_chunk is None:
            # 如果有一段处理失败，则尝试获取新的API密钥
            logger.warning(f"第 {i+1} 段处理失败，尝试获取新的API密钥...")
            
            if key_manager:
                # 报告当前密钥错误
                key_manager.report_error(api_key)
                
                # 获取新的API密钥
                api_key_config = key_manager.get_key_config()
                if api_key_config:
                    api_key = api_key_config.get('key')
                    redirect_url = api_key_config.get('redirect_url')
                    model = api_key_config.get('model', config.DEFAULT_OPENAI_MODEL)
                    
                    # 重试当前段
                    logger.debug(f"使用新的API密钥重试第 {i+1} 段...")
                    condensed_chunk = _process_content_with_openai(
                        chunk, api_key, redirect_url, model, 
                        is_chunk=True, chunk_index=i+1, total_chunks=total_chunks
                    )
        
        if condensed_chunk is None:
            logger.error(f"第 {i+1} 段处理失败，已尝试所有可用的API密钥")
            return None
        
        condensed_chunks.append(condensed_chunk)
    
    # 合并处理结果
    condensed_content = "\n\n".join(condensed_chunks)
    
    if key_manager:
        # 报告成功
        key_manager.report_success(api_key)
        
    return condensed_content

def _process_content_with_openai(content: str, api_key: str, redirect_url: str, model: str, 
                               is_chunk: bool = False, chunk_index: int = 0, total_chunks: int = 0) -> Optional[str]:
    """使用OpenAI API处理单个内容块
    
    Args:
        content: 要处理的内容
        api_key: API密钥
        redirect_url: API端点URL
        model: 模型名称
        is_chunk: 是否为分块处理的一部分
        chunk_index: 分块索引
        total_chunks: 总分块数
    
    Returns:
        Optional[str]: 处理后的内容，处理失败则返回None
    """
    # 构建提示词
    prefix = ""
    if is_chunk:
        prefix = f"这是一个小说的第{chunk_index}段，共{total_chunks}段。"
    
    system_message = f"{prefix}你是一个小说内容压缩工具。请将下面的小说内容精简到原来的30%-50%左右，同时保留所有重要情节、对话和描写，不要遗漏关键情节和人物。不要添加任何解释或总结，直接输出压缩后的内容。"
    
    # 构建正确的API URL格式
    final_api_url = redirect_url or config.DEFAULT_OPENAI_API_URL
    
    # 详细记录URL以便调试
    logger.debug(f"OpenAI API请求URL: {final_api_url}")
    
    # 构建OpenAI格式的请求体
    request_data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": content
            }
        ],
        "temperature": 0.2,
        "max_tokens": 8192,
        "top_p": 0.8,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    
    # 构建请求头 
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 添加重试逻辑
    max_retries = 3
    retry_delay = 5
    
    for retry in range(max_retries):
        try:
            # 发送请求
            logger.debug(f"发送OpenAI API请求 (尝试 {retry+1}/{max_retries})")
            response = requests.post(final_api_url, headers=headers, json=request_data, timeout=180)
            
            # 检查响应状态码
            if response.status_code == 200:
                response_json = response.json()
                
                # 提取生成的文本
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        condensed_text = choice["message"]["content"].strip()
                        
                        if condensed_text:
                            # 成功获取到压缩后的内容
                            return condensed_text
                        else:
                            logger.warning("OpenAI API返回了空内容")
                            # 尝试记录完整响应进行调试
                            logger.debug(f"完整响应: {json.dumps(response_json)}")
                
                # 响应格式不符合预期
                logger.error(f"OpenAI API响应格式异常")
                logger.debug(f"异常响应详情: {json.dumps(response_json)}")
                
            else:
                # 记录详细的错误信息
                logger.error(f"OpenAI API请求失败: HTTP {response.status_code}")
                try:
                    error_json = response.json()
                    logger.error(f"错误详情: {json.dumps(error_json)}")
                    
                    # 处理HTTP 429 - 配额超限错误
                    if response.status_code == 429:
                        retry_delay_seconds = 60  # 默认等待60秒
                        
                        logger.warning(f"OpenAI API配额超限，将等待{retry_delay_seconds}秒后重试...")
                        time.sleep(retry_delay_seconds)
                        # 如果是最后一次重试，不要增加重试计数，直接再试一次
                        if retry == max_retries - 1:
                            retry -= 1
                        continue  # 跳过下面的重试逻辑，直接开始下一次循环
                except:
                    logger.error(f"响应内容: {response.text}")
            
            # 如果还有重试次数，则等待后重试
            if retry < max_retries - 1:
                sleep_time = retry_delay * (2 ** retry)
                logger.debug(f"将在 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error(f"已达到最大重试次数，处理失败")
                
        except requests.exceptions.Timeout:
            logger.warning("OpenAI API请求超时")
            if retry < max_retries - 1:
                sleep_time = retry_delay * (2 ** retry)
                logger.debug(f"将在 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error("已达到最大重试次数，处理失败")
                
        except Exception as e:
            logger.error(f"OpenAI请求处理过程中发生错误: {e}")
            logger.debug(traceback.format_exc())
            if retry < max_retries - 1:
                sleep_time = retry_delay * (2 ** retry)
                logger.debug(f"将在 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error("已达到最大重试次数，处理失败")
    
    # 所有重试都失败
    return None

def print_processing_stats(original_content: str, condensed_content: str) -> None:
    """打印处理统计信息

    Args:
        original_content: 原始内容
        condensed_content: 处理后的内容
    """
    original_length = len(original_content)
    condensed_length = len(condensed_content)
    ratio = (condensed_length / original_length) * 100
    
    print(f"原文长度: {original_length} 字符")
    print(f"脱水后长度: {condensed_length} 字符")
    print(f"压缩比例: {ratio:.2f}%")
    
    # 检查压缩比例是否符合要求
    if ratio < config.MIN_CONDENSATION_RATIO - 5 or ratio > config.MAX_CONDENSATION_RATIO + 5:
        print(f"警告: 压缩比例 ({ratio:.2f}%) 不在预期范围内 ({config.MIN_CONDENSATION_RATIO}%-{config.MAX_CONDENSATION_RATIO}%)") 