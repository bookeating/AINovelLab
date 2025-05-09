#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API服务模块 - 处理Gemini API和OpenAI API的调用和响应
"""

import json
import requests
import time
import traceback
from typing import Dict, Optional, List, Any, Union, Tuple, Callable

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

# 尝试导入全局key_manager
try:
    from . import main
    global_key_manager = main.gemini_key_manager
    global_openai_key_manager = main.openai_key_manager
except (ImportError, AttributeError):
    global_key_manager = None
    global_openai_key_manager = None

def _get_api_key_config(api_type: str, api_key_config: Optional[Dict] = None, key_manager: Optional[APIKeyManager] = None) -> Optional[Dict]:
    """获取API密钥配置的通用函数
    
    Args:
        api_type: API类型，"gemini"或"openai"
        api_key_config: 可选的API密钥配置
        key_manager: 可选的API密钥管理器实例
    
    Returns:
        Optional[Dict]: API密钥配置字典，获取失败则返回None
    """
    # 如果已提供配置，直接返回
    if api_key_config is not None and isinstance(api_key_config, dict):
        return api_key_config
        
    # 如果没有提供key_manager，尝试使用或创建一个
    if key_manager is None:
        # 先尝试使用全局key_manager
        global_manager = global_key_manager if api_type == "gemini" else global_openai_key_manager
        
        if global_manager is not None:
            key_manager = global_manager
            logger.debug(f"使用全局{api_type.capitalize()} API密钥管理器")
        else:
            # 尝试从sys.modules中获取
            key_manager = _try_get_key_manager_from_modules(api_type)
            
            # 如果仍然无法获取，创建一个新的
            if key_manager is None:
                api_configs = config.GEMINI_API_CONFIG if api_type == "gemini" else config.OPENAI_API_CONFIG
                
                if not api_configs:
                    logger.error(f"未找到有效的{api_type.capitalize()} API密钥配置")
                    return None
                
                logger.warning(f"未找到现有的{api_type.capitalize()} API密钥管理器，创建临时管理器")
                key_manager = APIKeyManager(api_configs, config.DEFAULT_MAX_RPM)
    
    # 从key_manager获取API密钥配置
    api_key_config = key_manager.get_key_config() if key_manager else None
    
    if api_key_config is None:
        # 检查是否所有密钥都被跳过
        _log_key_unavailable_error(key_manager, api_type)
        return None
    
    return api_key_config

def _try_get_key_manager_from_modules(api_type: str) -> Optional[APIKeyManager]:
    """尝试从已加载的模块中获取key_manager
    
    Args:
        api_type: API类型，"gemini"或"openai"
    
    Returns:
        Optional[APIKeyManager]: 获取到的key_manager或None
    """
    try:
        import sys
        for module_name in ['main', f'novel_condenser.main']:
            if module_name in sys.modules:
                main_module = sys.modules[module_name]
                manager_name = f"{api_type}_key_manager"
                if hasattr(main_module, manager_name) and getattr(main_module, manager_name) is not None:
                    key_manager = getattr(main_module, manager_name)
                    logger.debug(f"从{module_name}模块动态获取到{api_type.capitalize()} API密钥管理器")
                    return key_manager
        return None
    except Exception as e:
        logger.debug(f"尝试动态获取{api_type.capitalize()} key_manager时出错: {e}")
        return None

def _log_key_unavailable_error(key_manager: Optional[APIKeyManager], api_type: str) -> None:
    """记录API密钥不可用的错误
    
    Args:
        key_manager: API密钥管理器
        api_type: API类型，"gemini"或"openai"
    """
    if key_manager and hasattr(key_manager, 'skipped_keys'):
        api_configs = config.GEMINI_API_CONFIG if api_type == "gemini" else config.OPENAI_API_CONFIG
        valid_keys = [api_conf['key'] for api_conf in api_configs 
                    if api_conf['key'] not in key_manager.skipped_keys]
        if not valid_keys:
            logger.error(f"所有{api_type.capitalize()} API密钥都因失败次数过多被跳过，脱水过程结束")
            return
    
    logger.error(f"无法获取可用的{api_type.capitalize()} API密钥，请检查配置或等待密钥冷却期结束")

def _build_api_url(api_type: str, api_key: str, redirect_url: str, model: str) -> str:
    """构建API请求URL
    
    Args:
        api_type: API类型，"gemini"或"openai"
        api_key: API密钥
        redirect_url: 重定向URL
        model: 模型名称
    
    Returns:
        str: 构建好的API URL
    """
    # 初始化API URL
    final_api_url = ""
    
    if api_type == "gemini":
        # 处理Gemini API URL
        final_api_url = _build_gemini_url(redirect_url, model)
        
        # 添加API密钥(如果需要)
        if "key=" not in final_api_url:
            # 对官方Google API或某些代理添加key参数
            if not redirect_url or "generativelanguage.googleapis.com" in redirect_url:
                final_api_url += "&key=" + api_key if "?" in final_api_url else "?key=" + api_key
    else:
        # 处理OpenAI API URL
        final_api_url = _build_openai_url(redirect_url)
    
    logger.debug(f"{api_type.capitalize()} API请求URL: {final_api_url}")
    return final_api_url

def _build_gemini_url(redirect_url: str, model: str) -> str:
    """构建Gemini API URL
    
    Args:
        redirect_url: 重定向URL
        model: 模型名称
    
    Returns:
        str: Gemini API URL
    """
    if not redirect_url:
        # 使用默认URL
        return f"{config.DEFAULT_GEMINI_API_URL}{model}:generateContent"
        
    # 使用提供的重定向URL
    url = redirect_url.strip()
    
    # 如果URL不包含:generateContent后缀，添加模型和方法
    if ":generateContent" not in url:
        # 确保URL末尾有斜杠
        if not url.endswith('/'):
            url += '/'
        
        # 添加模型名和方法
        url += f"{model}:generateContent"
    
    return url

def _build_openai_url(redirect_url: str) -> str:
    """构建OpenAI API URL
    
    Args:
        redirect_url: 重定向URL
    
    Returns:
        str: OpenAI API URL
    """
    if not redirect_url:
        # 使用官方OpenAI端点
        return config.DEFAULT_OPENAI_API_URL
    
    # 使用提供的redirect_url作为完整URL
    url = redirect_url.strip()
    
    # 检查URL是否已经包含chat/completions路径
    if 'chat/completions' not in url:
        # URL不包含必要的路径，需要添加
        url = url.rstrip('/') + '/chat/completions'
    elif url.endswith('/') and not url.endswith('/?'):
        # 移除末尾的斜杠（但保留查询字符串中的斜杠）
        url = url.rstrip('/')
    
    return url

def _build_request_headers(api_type: str, api_key: str, redirect_url: str) -> Dict:
    """构建API请求头
    
    Args:
        api_type: API类型，"gemini"或"openai"
        api_key: API密钥
        redirect_url: 重定向URL
    
    Returns:
        Dict: 请求头字典
    """
    # 基础请求头
    headers = {"Content-Type": "application/json"}
    
    # 根据API类型添加特定头部
    if api_type == "gemini":
        # 仅在特定情况下添加API密钥到头部
        if redirect_url and "key=" not in redirect_url:
            is_non_official = "aliyahzombie" in redirect_url or "generativelanguage.googleapis.com" not in redirect_url
            if is_non_official:
                headers["x-goog-api-key"] = api_key
    else:
        # OpenAI API需要Bearer认证
        headers["Authorization"] = f"Bearer {api_key}"
        headers["User-Agent"] = "Mozilla/5.0 OpenAI API Client"
        
    return headers

def _build_request_data(api_type: str, model: str, system_prompt: str, content: str) -> Dict:
    """构建API请求数据
    
    Args:
        api_type: API类型，"gemini"或"openai"
        model: 模型名称
        system_prompt: 系统提示词
        content: 内容文本
    
    Returns:
        Dict: 请求数据字典
    """
    # 从配置获取通用生成参数
    temperature = config.LLM_GENERATION_PARAMS.get("temperature", 0.2)
    top_p = config.LLM_GENERATION_PARAMS.get("top_p", 0.8)
    max_tokens = config.LLM_GENERATION_PARAMS.get("max_tokens", 8192)
    
    if api_type == "gemini":
        # Gemini格式的请求数据
        top_k = config.LLM_GENERATION_PARAMS.get("top_k", 40)
        
        return {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt},
                        {"text": content}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "topK": top_k,
                "topP": top_p,
                "maxOutputTokens": max_tokens,
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
    else:
        # OpenAI格式的请求数据
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

def _process_content_in_chunks(content: str, api_type: str, api_key: str, redirect_url: str, model: str, 
                              key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """通用的内容分块处理函数
    
    Args:
        content: 要处理的内容
        api_type: API类型，"gemini"或"openai"
        api_key: API密钥
        redirect_url: API端点URL
        model: 模型名称
        key_manager: 可选的API密钥管理器
    
    Returns:
        Optional[str]: 处理后的内容，处理失败则返回None
    """
    # 计算内容长度，超长的内容需要分段处理
    content_length = len(content)
    max_chunk_length = 20000  # 单次处理的最大字符数
    
    # 如果内容长度小于阈值，则直接处理
    if content_length <= max_chunk_length:
        return _process_content_with_api(content, api_type, api_key, redirect_url, model)
    
    # 分段处理
    logger.debug(f"内容长度为 {content_length} 字符，将分段处理...")
    
    # 分段计算
    total_chunks = (content_length + max_chunk_length - 1) // max_chunk_length
    logger.debug(f"将分为 {total_chunks} 段进行处理")
    
    # 存储各段的处理结果
    condensed_chunks = []
    
    # 分段处理
    for i in range(total_chunks):
        start_pos = i * max_chunk_length
        end_pos = min(start_pos + max_chunk_length, content_length)
        chunk = content[start_pos:end_pos]
        
        logger.debug(f"处理第 {i+1}/{total_chunks} 段，字符范围: {start_pos}-{end_pos}...")
        
        # 处理当前段
        condensed_chunk = _process_chunk_with_retry(
            chunk, api_type, api_key, redirect_url, model, 
            i+1, total_chunks, key_manager
        )
        
        if condensed_chunk is None:
            logger.error(f"第 {i+1} 段处理失败，已尝试所有可用的API密钥")
            return None
        
        condensed_chunks.append(condensed_chunk)
    
    # 合并处理结果
    condensed_content = "\n\n".join(condensed_chunks)
    
    if key_manager:
        # 报告最终成功
        key_manager.report_success(api_key)
        
    return condensed_content

def _process_chunk_with_retry(chunk: str, api_type: str, api_key: str, redirect_url: str, model: str,
                             chunk_index: int, total_chunks: int, 
                             key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """带重试机制处理内容块
    
    Args:
        chunk: 要处理的内容块
        api_type: API类型，"gemini"或"openai"
        api_key: API密钥
        redirect_url: API端点URL
        model: 模型名称
        chunk_index: 分块索引
        total_chunks: 总分块数
        key_manager: 可选的API密钥管理器
    
    Returns:
        Optional[str]: 处理后的内容，处理失败则返回None
    """
    # 先尝试处理当前段
    condensed_chunk = _process_content_with_api(
        chunk, api_type, api_key, redirect_url, model, 
        is_chunk=True, chunk_index=chunk_index, total_chunks=total_chunks
    )
    
    # 如果处理失败且有key_manager，尝试获取新的API密钥重试
    if condensed_chunk is None and key_manager:
        logger.warning(f"第 {chunk_index} 段处理失败，尝试获取新的API密钥...")
        
        # 报告当前密钥错误
        key_manager.report_error(api_key)
        
        # 获取新的API密钥
        api_key_config = key_manager.get_key_config()
        if api_key_config:
            new_api_key = api_key_config.get('key')
            new_redirect_url = api_key_config.get('redirect_url', '')
            default_model = config.DEFAULT_GEMINI_MODEL if api_type == "gemini" else config.DEFAULT_OPENAI_MODEL
            new_model = api_key_config.get('model', default_model)
            
            # 使用新的API密钥重试
            logger.debug(f"使用新的API密钥重试第 {chunk_index} 段...")
            return _process_content_with_api(
                chunk, api_type, new_api_key, new_redirect_url, new_model, 
                is_chunk=True, chunk_index=chunk_index, total_chunks=total_chunks
            )
    
    return condensed_chunk

def _process_content_with_api(content: str, api_type: str, api_key: str, redirect_url: str, model: str, 
                             is_chunk: bool = False, chunk_index: int = 0, total_chunks: int = 0) -> Optional[str]:
    """通用的API内容处理函数
    
    Args:
        content: 要处理的内容
        api_type: API类型，"gemini"或"openai"
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
    system_prompt = generate_novel_condenser_prompt(is_chunk, chunk_index, total_chunks)
    
    # 构建API URL
    final_api_url = _build_api_url(api_type, api_key, redirect_url, model)
    
    # 构建请求头
    headers = _build_request_headers(api_type, api_key, redirect_url)
    
    # 构建请求数据
    request_data = _build_request_data(api_type, model, system_prompt, content)
    
    # 从配置获取重试相关参数
    max_retries = config.LLM_GENERATION_PARAMS.get("max_retries", 3)
    retry_delay = config.LLM_GENERATION_PARAMS.get("retry_delay", 5)
    
    # 从配置获取超时时间
    timeout_settings = config.LLM_GENERATION_PARAMS.get("timeout", {
        "official_api": 120,
        "third_party_api": 180
    })
    
    # 设置超时时间 - 对于第三方API增加超时时间，它们通常响应较慢
    is_official_api = False
    if api_type == "gemini":
        is_official_api = not redirect_url or "generativelanguage.googleapis.com" in redirect_url
    else:
        is_official_api = not redirect_url or "openai.com" in redirect_url
        
    timeout = timeout_settings.get("official_api", 120) if is_official_api else timeout_settings.get("third_party_api", 180)
    logger.debug(f"设置请求超时: {timeout}秒")
    
    # 使用通用API请求函数
    response_json = _make_api_request(
        url=final_api_url, 
        headers=headers, 
        data=request_data, 
        api_type=api_type,
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout
    )
    
    if response_json:
        # 解析响应
        condensed_text = _parse_llm_response(response_json, api_type)
        if condensed_text:
            return condensed_text
        else:
            logger.warning(f"{api_type.capitalize()} API返回了空内容或无法识别的响应格式")
            # 尝试记录完整响应进行调试
            logger.debug(f"完整响应: {json.dumps(response_json)}")
    
    # 请求失败
    return None

def _make_api_request(url: str, headers: Dict, data: Dict, api_type: str, max_retries: int = 3, 
                     retry_delay: int = 5, timeout: int = 120) -> Optional[Dict]:
    """通用的API请求处理函数
    
    Args:
        url: API请求URL
        headers: 请求头
        data: 请求数据
        api_type: API类型，"gemini"或"openai"
        max_retries: 最大重试次数
        retry_delay: 基础重试延迟（秒）
        timeout: 请求超时时间（秒）
    
    Returns:
        Optional[Dict]: API响应数据，请求失败则返回None
    """
    for retry in range(max_retries):
        try:
            # 发送请求
            logger.debug(f"发送{api_type.capitalize()} API请求 (尝试 {retry+1}/{max_retries})")
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
            
            # 检查响应状态码
            if response.status_code == 200:
                return response.json()
                
            # 处理非200响应
            logger.error(f"{api_type.capitalize()} API请求失败: HTTP {response.status_code}")
            
            # 尝试解析错误响应
            error_json = None
            try:
                error_json = response.json()
                logger.error(f"错误详情: {json.dumps(error_json)}")
            except:
                logger.error(f"响应内容: {response.text}")
                
            # 处理配额超限错误，可能需要特殊等待
            if response.status_code == 429:
                retry_delay_seconds = _get_retry_delay_for_rate_limit(error_json, api_type)
                logger.warning(f"{api_type.capitalize()} API配额超限，将等待{retry_delay_seconds}秒后重试...")
                time.sleep(retry_delay_seconds)
                
                # 如果是最后一次重试，给予一次额外机会
                if retry == max_retries - 1:
                    retry -= 1
                continue
                
        except requests.exceptions.Timeout:
            logger.warning(f"{api_type.capitalize()} API请求超时")
            
        except Exception as e:
            logger.error(f"{api_type.capitalize()}请求处理过程中发生错误: {e}")
            logger.debug(traceback.format_exc())
            
        # 只要不是最后一次尝试，就等待后重试
        if retry < max_retries - 1:
            sleep_time = _calculate_exponential_backoff(retry_delay, retry)
            logger.debug(f"将在 {sleep_time} 秒后重试...")
            time.sleep(sleep_time)
        else:
            logger.error("已达到最大重试次数，处理失败")
    
    # 所有重试都失败
    return None

def _get_retry_delay_for_rate_limit(error_json: Optional[Dict], api_type: str) -> int:
    """获取配额超限情况下的重试延迟时间
    
    Args:
        error_json: 错误响应JSON
        api_type: API类型
        
    Returns:
        int: 建议的重试延迟秒数
    """
    retry_delay_seconds = 60  # 默认等待60秒
    
    # 尝试从Gemini错误信息中获取建议的重试延迟时间
    if api_type == "gemini" and error_json and "error" in error_json and "details" in error_json["error"]:
        for detail in error_json["error"]["details"]:
            if "@type" in detail and detail["@type"] == "type.googleapis.com/google.rpc.RetryInfo":
                if "retryDelay" in detail:
                    delay_str = detail["retryDelay"]
                    if isinstance(delay_str, str) and 's' in delay_str:
                        try:
                            # 从错误信息提取延迟时间，并增加5秒冗余
                            retry_delay_seconds = int(delay_str.replace('s', '')) + 5
                        except ValueError:
                            pass
                            
    return retry_delay_seconds

def _calculate_exponential_backoff(base_delay: int, retry_count: int) -> int:
    """计算指数退避的延迟时间
    
    Args:
        base_delay: 基础延迟时间
        retry_count: 重试计数
        
    Returns:
        int: 延迟秒数
    """
    return base_delay * (2 ** retry_count)

def generate_novel_condenser_prompt(is_chunk: bool = False, chunk_index: int = 0, total_chunks: int = 0) -> str:
    """生成小说内容压缩的提示词
    
    Args:
        is_chunk: 是否为分块处理的一部分
        chunk_index: 分块索引
        total_chunks: 总分块数
    
    Returns:
        str: 生成的提示词
    """
    # 获取基础提示词模板
    prompt_template = config.PROMPT_TEMPLATES.get("novel_condenser", 
                      "你是一个小说内容压缩工具。请将下面的小说内容精简到原来的{min_ratio}%-{max_ratio}%左右，同时保留所有重要情节、对话和描写，不要遗漏关键情节和人物。不要添加任何解释或总结，直接输出压缩后的内容。")
    
    # 替换变量
    prompt = prompt_template.format(
        min_ratio=config.MIN_CONDENSATION_RATIO,
        max_ratio=config.MAX_CONDENSATION_RATIO
    )
    
    # 如果是分块处理，添加分块前缀
    if is_chunk:
        chunk_prefix_template = config.PROMPT_TEMPLATES.get("chunk_prefix", 
                               "这是一个小说的第{chunk_index}段，共{total_chunks}段。")
        
        # 替换变量
        chunk_prefix = chunk_prefix_template.format(
            chunk_index=chunk_index,
            total_chunks=total_chunks
        )
        
        # 组合前缀和提示词
        prompt = f"{chunk_prefix} {prompt}"
    
    return prompt

def condense_novel_gemini(content: str, api_key_config: Optional[Dict] = None, key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """使用Gemini API对小说内容进行压缩处理
    
    Args:
        content: 小说内容
        api_key_config: API密钥配置
        key_manager: API密钥管理器实例

    Returns:
        Optional[str]: 压缩后的内容，处理失败则返回None
    """
    return _condense_novel_with_api("gemini", content, api_key_config, key_manager)

def condense_novel_openai(content: str, api_key_config: Optional[Dict] = None, key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """使用OpenAI API对小说内容进行压缩处理
    
    Args:
        content: 小说内容
        api_key_config: API密钥配置
        key_manager: API密钥管理器实例

    Returns:
        Optional[str]: 压缩后的内容，处理失败则返回None
    """
    return _condense_novel_with_api("openai", content, api_key_config, key_manager)

def _condense_novel_with_api(api_type: str, content: str, api_key_config: Optional[Dict] = None, 
                            key_manager: Optional[APIKeyManager] = None) -> Optional[str]:
    """通用API小说内容压缩处理函数
    
    Args:
        api_type: API类型，"gemini"或"openai"
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
    api_key_config = _get_api_key_config(api_type, api_key_config, key_manager)
    if api_key_config is None:
        return None
    
    # 从api_key_config中获取密钥信息
    api_key = api_key_config.get('key', '')
    redirect_url = api_key_config.get('redirect_url', '')
    default_model = config.DEFAULT_GEMINI_MODEL if api_type == "gemini" else config.DEFAULT_OPENAI_MODEL
    model = api_key_config.get('model', default_model)
    
    # 检查API密钥是否有效
    if not api_key:
        logger.error(f"{api_type.capitalize()} API密钥为空")
        return None
    
    # 使用通用分块处理函数
    return _process_content_in_chunks(content, api_type, api_key, redirect_url, model, key_manager)

def _parse_llm_response(response_json: Dict, api_type: str = "gemini") -> Optional[str]:
    """解析LLM API响应，支持多种格式
    
    Args:
        response_json: API响应的JSON数据
        api_type: API类型，"gemini"或"openai"
    
    Returns:
        Optional[str]: 解析出的文本内容，解析失败则返回None
    """
    # 尝试不同的解析方法，按优先级排序
    parsers = [
        # 标准格式解析器
        lambda: _parse_standard_format(response_json, api_type),
        # 通用格式解析器
        lambda: _parse_generic_format(response_json),
    ]
    
    # 尝试每种解析方法
    for parser in parsers:
        result = parser()
        if result:
            return result.strip()
    
    return None

def _parse_standard_format(response_json: Dict, api_type: str) -> Optional[str]:
    """解析标准响应格式
    
    Args:
        response_json: API响应的JSON数据
        api_type: API类型，"gemini"或"openai"
    
    Returns:
        Optional[str]: 解析出的文本内容，解析失败则返回None
    """
    if api_type == "gemini":
        # 解析标准Gemini格式
        if "candidates" in response_json:
            try:
                parts = response_json["candidates"][0]["content"]["parts"]
                collected_text = []
                
                for part in parts:
                    if "text" in part:
                        collected_text.append(part["text"])
                    elif "thing" in part:
                        thing = part["thing"]
                        if isinstance(thing, dict):
                            if "thinking" in thing:
                                collected_text.append(thing["thinking"])
                            elif "value" in thing:
                                collected_text.append(thing["value"])
                        elif isinstance(thing, str):
                            collected_text.append(thing)
                
                # 合并所有文本
                if collected_text:
                    return "\n".join([text for text in collected_text if text.strip()])
            except (KeyError, IndexError):
                pass
    else:
        # 解析标准OpenAI格式
        if "choices" in response_json and response_json["choices"]:
            try:
                return response_json["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                pass
    
    return None

def _parse_generic_format(response_json: Dict) -> Optional[str]:
    """解析通用响应格式，支持各种第三方API
    
    Args:
        response_json: API响应的JSON数据
    
    Returns:
        Optional[str]: 解析出的文本内容，解析失败则返回None
    """
    # 尝试从常见字段中获取内容
    common_fields = ["response", "output", "content"]
    for field in common_fields:
        if field in response_json and response_json[field]:
            return str(response_json[field])
    
    # 尝试从结果数组中获取内容
    if "results" in response_json:
        results = response_json["results"]
        if isinstance(results, list) and results:
            return str(results[0])
        elif isinstance(results, str):
            return results
    
    # 检查嵌套在data字段中的内容
    if "data" in response_json:
        data = response_json["data"]
        
        # 检查data是否是字符串
        if isinstance(data, str):
            return data
            
        # 检查data是否是对象
        if not isinstance(data, dict):
            return None
            
        # 尝试从data中的常见字段获取内容
        for field in common_fields:
            if field in data:
                return str(data[field])
        
        # 尝试从data中的candidates获取内容
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            if isinstance(candidate, dict) and "content" in candidate:
                return candidate["content"]
            elif isinstance(candidate, str):
                return candidate
        
        # 尝试从data中的choices获取内容
        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            if isinstance(choice, dict) and "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            elif isinstance(choice, str):
                return choice
                
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