#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小说处理工具的工作线程和日志重定向类
"""

import os
import sys
import time
import io
import logging
import threading

from PyQt5.QtCore import QThread, pyqtSignal

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 从core模块导入处理脚本
try:
    from core import epub_splitter
    from core import txt_to_epub
    # 导入core.novel_condenser包及其子模块
    from core.novel_condenser import config, file_utils, api_service, key_manager, stats
    import core.novel_condenser.main as main_module  # 直接导入整个main模块
    from core.novel_condenser.main import process_single_file, process_files_concurrently  # 直接导入需要的函数
    from core.novel_condenser.file_utils import OUTPUT_DIR
except ImportError:
    from src.core import epub_splitter
    from src.core import txt_to_epub
    # 导入core.novel_condenser包及其子模块
    from src.core.novel_condenser import config, file_utils, api_service, key_manager, stats
    import src.core.novel_condenser.main as main_module  # 直接导入整个main模块
    from src.core.novel_condenser.main import process_single_file, process_files_concurrently  # 直接导入需要的函数
    from src.core.novel_condenser.file_utils import OUTPUT_DIR

import re  # 导入re模块，替代原来的novel_condenser.re引用

class LogRedirector(io.StringIO):
    """用于重定向日志输出的类"""
    
    def __init__(self, signal_handler):
        """
        初始化日志重定向器
        
        Args:
            signal_handler: 用于发送日志信号的处理函数
        """
        super().__init__()
        self.signal_handler = signal_handler
    
    def write(self, text):
        """
        写入文本时发送信号
        
        Args:
            text: 要写入的文本
        """
        if text and not text.isspace():
            self.signal_handler.emit(text)
            # 确保立即处理，不要等待缓冲区写满
            self.flush()
        return super().write(text)
    
    def flush(self):
        """刷新缓冲区，确保日志实时显示"""
        # 调用父类的flush方法
        super().flush()
        # 这里可以添加额外的刷新逻辑
        # 例如，强制GUI更新

class WorkerThread(QThread):
    """
    工作线程类，用于在后台执行耗时操作
    """
    update_progress = pyqtSignal(int, str)
    operation_complete = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)  # 日志信号
    
    def __init__(self, operation_type, args):
        """
        初始化工作线程
        
        Args:
            operation_type: 操作类型（'split', 'condense', 'merge'）
            args: 操作参数
        """
        super().__init__()
        self.operation_type = operation_type
        self.args = args
        self.is_running = True
        
        # 设置日志重定向
        self.stdout_redirector = None
        self.stderr_redirector = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def setup_log_redirect(self):
        """设置日志重定向，将标准输出和标准错误重定向到GUI"""
        self.stdout_redirector = LogRedirector(self.log_message)
        self.stderr_redirector = LogRedirector(self.log_message)
        
        # 保存原始的标准输出和标准错误流
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # 重定向标准输出和标准错误
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector
        
        # 配置logging模块，将其输出重定向到我们的日志系统
        logging_handler = logging.StreamHandler(self.stdout_redirector)
        logging_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # 获取根日志记录器
        root_logger = logging.getLogger()
        
        # 保存原始handlers
        self.original_handlers = root_logger.handlers.copy()
        
        # 清除原有handlers并添加我们的handler
        root_logger.handlers.clear()
        root_logger.addHandler(logging_handler)
        
        # 设置日志级别为INFO
        root_logger.setLevel(logging.INFO)
    
    def restore_log_redirect(self):
        """恢复原始的标准输出和标准错误"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # 恢复logging的原始handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        for handler in self.original_handlers:
            root_logger.addHandler(handler)
    
    def run(self):
        """线程执行的主函数"""
        try:
            # 设置日志重定向
            self.setup_log_redirect()
            
            # 记录开始日志
            print(f"开始执行{self._get_operation_name()}操作...", flush=True)
            
            if self.operation_type == 'split':
                self._run_split_operation()
            elif self.operation_type == 'condense':
                self._run_condense_operation()
            elif self.operation_type == 'merge':
                self._run_merge_operation()
                
            self.operation_complete.emit(True, "操作成功完成")
        except Exception as e:
            print(f"操作失败: {str(e)}", flush=True)
            self.operation_complete.emit(False, f"操作失败: {str(e)}")
        finally:
            # 恢复标准输出和标准错误
            self.restore_log_redirect()
    
    def _get_operation_name(self):
        """获取操作类型的中文名称"""
        if self.operation_type == 'split':
            return "EPUB转TXT"
        elif self.operation_type == 'condense':
            return "脱水处理"
        elif self.operation_type == 'merge':
            return "TXT转EPUB"
        return "未知操作"
    
    def _run_split_operation(self):
        """执行EPUB分割操作"""
        epub_path = self.args.get('epub_path')
        output_dir = self.args.get('output_dir')
        chapters_per_file = self.args.get('chapters_per_file', 1)
        
        print(f"正在分割EPUB文件: {epub_path}", flush=True)
        print(f"输出目录: {output_dir}", flush=True)
        print(f"每个文件章节数: {chapters_per_file}", flush=True)
        
        # 调用epub_splitter的函数
        result = epub_splitter.split_epub(
            epub_path, 
            output_dir, 
            chapters_per_file=chapters_per_file
        )
        
        # 模拟进度更新
        for i in range(101):
            if not self.is_running:
                break
            self.update_progress.emit(i, f"正在处理: {i}%")
            time.sleep(0.02)
        
        print("EPUB分割完成", flush=True)
    
    def _run_condense_operation(self):
        """执行脱水操作"""
        input_files = self.args.get('input_files', [])
        start_chapter = self.args.get('start_chapter', 1)
        end_chapter = self.args.get('end_chapter', len(input_files))
        output_dir = self.args.get('output_dir', '')
        force_regenerate = self.args.get('force_regenerate', False)  # 获取强制生成参数
        api_type = self.args.get('api_type', 'gemini')  # 获取API类型，默认为gemini
        
        # 获取脱水比例参数
        min_ratio = self.args.get('min_condensation_ratio', config.MIN_CONDENSATION_RATIO)
        max_ratio = self.args.get('max_condensation_ratio', config.MAX_CONDENSATION_RATIO)
        target_ratio = self.args.get('target_condensation_ratio', config.TARGET_CONDENSATION_RATIO)
        
        # 更新全局配置
        config.MIN_CONDENSATION_RATIO = min_ratio
        config.MAX_CONDENSATION_RATIO = max_ratio
        config.TARGET_CONDENSATION_RATIO = target_ratio
        
        print(f"选择脱水章节范围: {start_chapter} - {end_chapter}", flush=True)
        if output_dir:
            print(f"脱水输出目录: {output_dir}", flush=True)
            # 设置全局输出目录
            file_utils.OUTPUT_DIR = output_dir
        
        print(f"强制生成模式: {'开启' if force_regenerate else '关闭'}", flush=True)
        print(f"API类型: {api_type}", flush=True)
        print(f"脱水比例设置: 最小{min_ratio}% - 最大{max_ratio}% (目标{target_ratio}%)", flush=True)
        
        # 获取并显示并发数
        concurrency = 1
        gemini_concurrency = 0
        openai_concurrency = 0
        mixed_mode = api_type == "mixed"
        
        # 初始化API密钥管理器并获取并发数
        # 初始化Gemini API密钥管理器（如果使用Gemini或混合模式）
        if api_type == "gemini" or mixed_mode:
            if hasattr(main_module, 'gemini_key_manager') and main_module.gemini_key_manager is not None:
                gemini_concurrency = main_module.gemini_key_manager.get_max_concurrency()
                gemini_api_count = len(config.GEMINI_API_CONFIG) if hasattr(config, 'GEMINI_API_CONFIG') else 0
            else:
                # 尝试初始化Gemini API密钥管理器
                try:
                    if hasattr(config, 'GEMINI_API_CONFIG') and config.GEMINI_API_CONFIG:
                        main_module.gemini_key_manager = key_manager.APIKeyManager(
                            config.GEMINI_API_CONFIG, 
                            config.DEFAULT_MAX_RPM
                        )
                        gemini_concurrency = main_module.gemini_key_manager.get_max_concurrency()
                        gemini_api_count = len(config.GEMINI_API_CONFIG)
                    else:
                        gemini_api_count = 0
                        print("未配置Gemini API密钥", flush=True)
                except Exception as e:
                    print(f"初始化Gemini API密钥管理器失败: {e}", flush=True)
                    gemini_api_count = 0
        
        # 初始化OpenAI API密钥管理器（如果使用OpenAI或混合模式）
        if api_type == "openai" or mixed_mode:
            if hasattr(main_module, 'openai_key_manager') and main_module.openai_key_manager is not None:
                openai_concurrency = main_module.openai_key_manager.get_max_concurrency()
                openai_api_count = len(config.OPENAI_API_CONFIG) if hasattr(config, 'OPENAI_API_CONFIG') else 0
            else:
                # 尝试初始化OpenAI API密钥管理器
                try:
                    if hasattr(config, 'OPENAI_API_CONFIG') and config.OPENAI_API_CONFIG:
                        main_module.openai_key_manager = key_manager.APIKeyManager(
                            config.OPENAI_API_CONFIG, 
                            config.DEFAULT_MAX_RPM
                        )
                        openai_concurrency = main_module.openai_key_manager.get_max_concurrency()
                        openai_api_count = len(config.OPENAI_API_CONFIG)
                    else:
                        openai_api_count = 0
                        print("未配置OpenAI API密钥", flush=True)
                except Exception as e:
                    print(f"初始化OpenAI API密钥管理器失败: {e}", flush=True)
                    openai_api_count = 0
        
        # 计算总并发数和总API密钥数量
        if mixed_mode:
            concurrency = gemini_concurrency + openai_concurrency
            api_count = gemini_api_count + openai_api_count
            print(f"API类型: {api_type}", flush=True)
            print(f"当前API密钥并发数: {concurrency} (Gemini={gemini_concurrency}, OpenAI={openai_concurrency})", flush=True)
            print(f"可用API密钥数量: {api_count} (Gemini={gemini_api_count}, OpenAI={openai_api_count})", flush=True)
        elif api_type == "gemini":
            concurrency = gemini_concurrency
            api_count = gemini_api_count
            print(f"API类型: {api_type}", flush=True)
            print(f"当前API密钥并发数: {concurrency}", flush=True)
            print(f"可用API密钥数量: {api_count}", flush=True)
        else:  # openai
            concurrency = openai_concurrency
            api_count = openai_api_count
            print(f"API类型: {api_type}", flush=True)
            print(f"当前API密钥并发数: {concurrency}", flush=True)
            print(f"可用API密钥数量: {api_count}", flush=True)
        
        # 筛选出我们需要处理的章节
        files_to_process = []
        for file_path in input_files:
            # 解析文件名中的章节编号
            file_name = os.path.basename(file_path)
            match = re.search(r'_\[?(\d+)', file_name)
            if match:
                chapter_num = int(match.group(1))
                if start_chapter <= chapter_num <= end_chapter:
                    files_to_process.append(file_path)
        
        total_files = len(files_to_process)
        print(f"共有{total_files}个章节需要脱水处理", flush=True)
        
        if total_files == 0:
            print("没有找到符合条件的章节，操作取消", flush=True)
            return
            
        # 修改处理模式选择逻辑，只在无法使用并发时才使用顺序处理
        if concurrency < 1:
            print(f"并发数小于1 (concurrency={concurrency})，使用顺序处理模式", flush=True)
            use_concurrent = False
        elif total_files < 2:
            print(f"章节数少于2 (total_files={total_files})，使用顺序处理模式", flush=True)
            use_concurrent = False
        else:
            print(f"并发数={concurrency}，章节数={total_files}，使用并发处理模式", flush=True)
            use_concurrent = True
            
        if use_concurrent:
            # 在使用并发处理前，先检查哪些文件需要处理
            if not force_regenerate:
                files_need_processing = []
                skipped_files = []
                
                for file_path in files_to_process:
                    # 检查目标文件是否存在
                    base_name = os.path.basename(file_path)
                    output_file_path = os.path.join(output_dir, base_name)
                    if os.path.exists(output_file_path):
                        # 检查文件大小，如果小于300个字符，则重新处理
                        try:
                            with open(output_file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            if len(content) < 300:
                                print(f"已存在的脱水文件 {base_name} 小于300个字符，将重新脱水", flush=True)
                                files_need_processing.append(file_path)
                            else:
                                skipped_files.append(file_path)
                                print(f"跳过已存在的文件: {base_name}", flush=True)
                        except Exception as e:
                            print(f"检查已存在文件时出错: {e}，将重新脱水", flush=True)
                            files_need_processing.append(file_path)
                    else:
                        files_need_processing.append(file_path)
                
                print(f"跳过了{len(skipped_files)}个已存在的文件", flush=True)
                
                # 更新要处理的文件列表
                files_to_process = files_need_processing
                total_files = len(files_to_process)
                
                if total_files == 0:
                    print("所有文件都已处理，无需再次生成", flush=True)
                    self.update_progress.emit(100, "所有文件均已存在，无需处理")
                    return
                
                print(f"需要处理的文件数量: {total_files}", flush=True)
            
            print(f"开始并发处理文件，并发数: {concurrency}", flush=True)
            
            # 记录开始时间
            start_time = time.time()
            
            # 重置统计数据
            stats.reset_statistics()
            stats.statistics["start_time"] = time.time()
            stats.statistics["end_time"] = 0
            stats.statistics["total_files"] = total_files
            stats.statistics["success_count"] = 0
            stats.statistics["failed_count"] = 0
            stats.statistics["retry_count"] = 0
            stats.statistics["file_stats"] = {}
            stats.statistics["condensation_ratios"] = []
            stats.statistics["total_characters_original"] = 0
            stats.statistics["total_characters_condensed"] = 0
            
            # 创建进度监控线程，定期更新进度条
            class ProgressMonitorThread(threading.Thread):
                def __init__(self, worker_thread):
                    super().__init__()
                    self.worker_thread = worker_thread
                    self.last_count = 0
                    
                def run(self):
                    while self.is_running and self.worker_thread.is_running:
                        # 计算已处理文件数
                        if hasattr(stats, 'statistics'):
                            current_processed = len(stats.statistics.get("file_stats", {}))
                            if current_processed > self.last_count:
                                progress = int((current_processed / total_files) * 100)
                                self.worker_thread.update_progress.emit(
                                    progress, 
                                    f"已处理: {current_processed}/{total_files} 个文件"
                                )
                                self.last_count = current_processed
                        
                        # 短暂休眠，避免过度消耗CPU
                        time.sleep(0.5)
            
            # 创建并启动进度监控线程
            progress_thread = ProgressMonitorThread(self)
            progress_thread.daemon = True
            progress_thread.is_running = True
            progress_thread.start()
            
            # 保存对线程的引用，以便在stop方法中可以访问
            self.progress_thread = progress_thread
            
            try:
                # 使用导入的process_files_concurrently函数
                print(f"启动并发处理，并发数: {concurrency}", flush=True)
                # 直接调用process_files_concurrently，而不是通过main_module
                success_count, failed_file_dict = process_files_concurrently(
                    files_to_process, 
                    max_workers=concurrency,
                    api_type=api_type,  # 使用选择的API类型
                    force_regenerate=force_regenerate,
                    update_progress_func=lambda current, total, status=None: self.update_progress.emit(
                        int(current * 100 / total), f"脱水处理进度: {current}/{total}{' - ' + status if status else ''}"
                    )
                )
                
                print(f"\n处理结果: 成功 {success_count}/{total_files} 个文件", flush=True)
                if failed_file_dict:
                    print("\n处理失败的文件:", flush=True)
                    for file_path, tries in failed_file_dict.items():
                        print(f"  - {os.path.basename(file_path)} (尝试 {tries} 次)", flush=True)
            except Exception as e:
                print(f"并发处理过程中出错: {e}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
            finally:
                # 确保在任何情况下都停止进度监控线程
                if progress_thread and hasattr(progress_thread, 'is_running'):
                    progress_thread.is_running = False
                    try:
                        progress_thread.join(timeout=1.0)
                    except:
                        pass
                
                # 清除线程引用
                self.progress_thread = None
            
            # 计算处理时间
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            
            time_str = ""
            if hours > 0:
                time_str += f"{int(hours)}小时"
            if minutes > 0:
                time_str += f"{int(minutes)}分钟"
            time_str += f"{int(seconds)}秒"
            
            print(f"\n总耗时: {time_str}", flush=True)
            
            # 最终进度更新
            self.update_progress.emit(100, "处理完成")
        else:
            # 顺序处理
            print("执行顺序处理...", flush=True)
            processed_count = 0
            skipped_count = 0
            
            for i, file_path in enumerate(files_to_process):
                if not self.is_running:
                    print("用户取消操作", flush=True)
                    break
                    
                base_name = os.path.basename(file_path)
                print(f"处理文件 {i+1}/{total_files}: {base_name}", flush=True)
                
                # 更新进度
                progress = int(((i+1) / total_files) * 100)
                self.update_progress.emit(progress, f"处理: {i+1}/{total_files}")
                
                try:
                    # 使用原始API，不传递output_dir参数，因为已经设置了全局OUTPUT_DIR
                    process_single_file(file_path, api_type=api_type)
                    print(f"文件处理完成: {base_name}", flush=True)
                    processed_count += 1
                except Exception as e:
                    print(f"处理文件失败: {e}", flush=True)
            
            self.update_progress.emit(100, f"完成，跳过: {skipped_count}，处理: {processed_count}")
        
        # 重置输出目录
        file_utils.OUTPUT_DIR = None
        
        print("脱水处理完成", flush=True)
    
    def _run_merge_operation(self):
        """执行TXT到EPUB的合并操作"""
        txt_files = self.args.get('txt_files', [])
        output_path = self.args.get('output_path')
        title = self.args.get('title', '')
        author = self.args.get('author', '')
        
        # 如果没有文件，直接返回
        if not txt_files:
            print("没有选择TXT文件，无法执行合并操作", flush=True)
            raise Exception("没有选择TXT文件")
        
        # 获取文件所在的目录
        folder_path = os.path.dirname(txt_files[0])
        
        # 修改输出文件名，添加"_脱水"后缀
        if output_path:
            base_name, ext = os.path.splitext(output_path)
            output_path = f"{base_name}_脱水{ext}"
        
        print(f"开始将TXT合并为EPUB", flush=True)
        print(f"TXT文件所在目录: {folder_path}", flush=True)
        print(f"目录中TXT文件数量: {len(txt_files)}", flush=True)
        print(f"输出EPUB: {output_path}", flush=True)
        print(f"小说标题: {title or '(自动检测)'}", flush=True)
        print(f"作者: {author or '(未指定)'}", flush=True)
        
        # 调用txt_to_epub的函数来处理文件
        try:
            # 使用merge_txt_to_epub函数，需要传入文件夹路径而不是文件列表
            result = txt_to_epub.merge_txt_to_epub(
                folder_path,  # 第一个参数是位置参数，不使用命名参数方式
                output_path=output_path,
                author=author,
                novel_name=title
            )
            
            if not result:
                raise Exception("EPUB生成失败")
                
            print(f"EPUB文件已成功生成: {result}", flush=True)
        except Exception as e:
            print(f"合并TXT文件时出错: {str(e)}", flush=True)
            raise
        
        # 模拟进度更新
        for i in range(101):
            if not self.is_running:
                break
            self.update_progress.emit(i, f"正在合并: {i}%")
            time.sleep(0.02)
        
        print(f"合并完成，EPUB文件已生成: {output_path}", flush=True)
    
    def stop(self):
        """停止线程"""
        self.is_running = False
        
        # 停止当前可能运行的进度监控线程
        if hasattr(self, 'progress_thread') and hasattr(self.progress_thread, 'is_running'):
            self.progress_thread.is_running = False
            try:
                self.progress_thread.join(timeout=1.0)
            except:
                pass
        
        # 对于脱水处理，尝试设置停止事件以通知线程池
        if self.operation_type == 'condense':
            try:
                from core.novel_condenser.main import process_files_concurrently
                if hasattr(process_files_concurrently, 'progress_stopped'):
                    process_files_concurrently.progress_stopped.set()
            except ImportError:
                try:
                    from src.core.novel_condenser.main import process_files_concurrently
                    if hasattr(process_files_concurrently, 'progress_stopped'):
                        process_files_concurrently.progress_stopped.set()
                except:
                    pass
        
        # 对于已提交到线程池的任务，我们无法直接停止它们
        # 但是设置了标志位后，它们在下一个检查点应该会自行退出
        print("已发送停止信号到工作线程", flush=True) 