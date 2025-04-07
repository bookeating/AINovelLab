#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT转EPUB工具 - 将多个TXT文本文件合并为EPUB电子书

这个脚本可以将文件夹中的多个TXT文件按照特定命名规则合并为一个EPUB电子书，
便于在电子阅读器上阅读。
"""

import os
import re
import argparse
import logging
from pathlib import Path
from ebooklib import epub
from bs4 import BeautifulSoup


# 配置日志系统
def setup_logger(log_level=logging.INFO):
    """配置日志系统"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


# 创建全局日志对象
logger = setup_logger()


def parse_filename(filename):
    """
    从文件名中解析出小说名称、序号和章节名称
    
    Args:
        filename: 文件名字符串
        
    Returns:
        tuple: (小说名称, 章节序号, 章节标题)，解析失败则返回(None, None, None)
    """
    # 文件名格式：小说名称_[序号]_章节名称.txt 或 小说名称_序号_章节名称.txt
    pattern = r"(.+?)_\[?(\d+)\]?_(.+?)\.txt$"
    match = re.match(pattern, filename)
    if match:
        novel_name = match.group(1)
        chapter_number = int(match.group(2))
        chapter_title = match.group(3)
        return novel_name, chapter_number, chapter_title
    
    # 尝试其他可能的格式: 小说名_[开始-结束].txt，用于处理多章节合并文件
    pattern2 = r"(.+?)_\[(\d+)-(\d+)\]\.txt$"
    match = re.match(pattern2, filename)
    if match:
        novel_name = match.group(1)
        start_chapter = int(match.group(2))
        chapter_title = f"第{start_chapter}章"
        return novel_name, start_chapter, chapter_title
    
    logger.warning(f"无法解析文件名: {filename}，不符合命名规则")
    return None, None, None


def read_txt_content(file_path):
    """
    读取txt文件内容，自动处理编码问题
    
    Args:
        file_path: 文件路径对象或字符串
        
    Returns:
        str: 文件内容，读取失败则返回空字符串
    """
    file_path = Path(file_path)
    
    # 尝试使用不同编码读取文件
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
    
    for encoding in encodings:
        try:
            logger.debug(f"尝试使用 {encoding} 编码读取文件 {file_path.name}")
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                logger.debug(f"文件 {file_path.name} 使用 {encoding} 编码成功读取")
                return content
        except UnicodeDecodeError:
            continue
    
    logger.warning(f"警告：无法解码文件 {file_path}，将跳过该文件")
    return ""


def create_chapter_html(chapter_title, content):
    """
    创建章节的HTML内容
    
    Args:
        chapter_title: 章节标题
        content: 章节内容
        
    Returns:
        str: 格式化的HTML内容
    """
    try:
        # 优先尝试使用XML解析器
        soup = BeautifulSoup("<html><body></body></html>", "xml")
    except Exception as e:
        # 如果XML解析失败，回退到原来的lxml解析器
        logger.debug(f"XML解析失败，回退到lxml: {e}")
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
    
    body = soup.body
    
    # 添加章节标题
    title = soup.new_tag("h1")
    title.string = chapter_title
    body.append(title)
    
    # 将内容分段
    paragraphs = content.split('\n')
    for p_text in paragraphs:
        if p_text.strip():
            p = soup.new_tag("p")
            p.string = p_text.strip()
            body.append(p)
    
    return str(soup)


def detect_novel_name(txt_files, folder_path):
    """
    从文件名中检测小说名称
    
    Args:
        txt_files: TXT文件名列表
        folder_path: 文件夹路径
    
    Returns:
        str: 检测到的小说名称，如果无法检测则返回None
    """
    name_counter = {}
    
    for filename in txt_files:
        name, _, _ = parse_filename(filename)
        if name:
            name_counter[name] = name_counter.get(name, 0) + 1
    
    # 返回出现次数最多的小说名称
    if name_counter:
        most_common_name = max(name_counter.items(), key=lambda x: x[1])[0]
        logger.info(f"检测到小说名称: {most_common_name}")
        return most_common_name
    
    # 如果无法从文件名检测，则使用文件夹名称
    folder_name = Path(folder_path).name
    logger.info(f"无法从文件名检测小说名称，使用文件夹名称: {folder_name}")
    return folder_name


def extract_chapters(txt_files, folder_path, novel_name=None):
    """
    从文件列表中提取章节信息
    
    Args:
        txt_files: TXT文件名列表
        folder_path: 文件夹路径
        novel_name: 指定的小说名称，如果为None则自动检测
        
    Returns:
        tuple: (小说名称, 章节列表)
    """
    chapters = []
    detected_novel_name = None
    
    for filename in txt_files:
        name, number, title = parse_filename(filename)
        if name and number and title:
            if detected_novel_name is None:
                detected_novel_name = name
            
            # 确保所有文件属于同一本小说
            if name != detected_novel_name and novel_name is None:
                logger.warning(f"警告：文件 {filename} 的小说名称 '{name}' 与其他文件 '{detected_novel_name}' 不同")
            
            chapters.append({
                'filename': filename,
                'number': number,
                'title': title,
                'path': Path(folder_path) / filename
            })
    
    # 使用指定的小说名称或检测到的小说名称
    final_novel_name = novel_name or detected_novel_name or detect_novel_name(txt_files, folder_path)
    
    # 按章节编号排序
    chapters.sort(key=lambda x: x['number'])
    
    logger.info(f"从 {len(txt_files)} 个文件中提取了 {len(chapters)} 个有效章节")
    return final_novel_name, chapters


def create_epub_book(novel_name, chapters, author=None, language='zh-CN'):
    """
    创建EPUB书籍对象
    
    Args:
        novel_name: 小说名称
        chapters: 章节列表
        author: 作者名称
        language: 语言代码
        
    Returns:
        tuple: (epub书籍对象, epub章节列表, 目录列表, 书脊列表)
    """
    # 创建epub书籍
    book = epub.EpubBook()
    book.set_title(novel_name)
    book.set_language(language)
    
    if author:
        book.add_author(author)
    
    # 添加章节
    epub_chapters = []
    toc = []
    spine = ['nav']
    
    return book, epub_chapters, toc, spine


def add_chapters_to_book(book, chapters, epub_chapters, toc, spine):
    """
    将章节添加到EPUB书籍
    
    Args:
        book: EPUB书籍对象
        chapters: 章节信息列表
        epub_chapters: EPUB章节对象列表
        toc: 目录列表
        spine: 书脊列表
        
    Returns:
        int: 成功添加的章节数
    """
    added_chapters = 0
    
    for chapter in chapters:
        try:
            # 读取章节内容
            content = read_txt_content(chapter['path'])
            if not content:
                logger.warning(f"跳过空章节: {chapter['title']}")
                continue
            
            # 创建epub章节
            chapter_id = f"chapter_{chapter['number']}"
            epub_chapter = epub.EpubHtml(
                title=chapter['title'],
                file_name=f"{chapter_id}.xhtml",
                lang='zh-CN'
            )
            
            # 设置章节内容
            epub_chapter.content = create_chapter_html(chapter['title'], content)
            
            # 添加到书籍
            book.add_item(epub_chapter)
            epub_chapters.append(epub_chapter)
            toc.append(epub.Link(f"{chapter_id}.xhtml", chapter['title'], chapter_id))
            spine.append(epub_chapter)
            
            added_chapters += 1
            logger.debug(f"已添加章节: {chapter['title']}")
            
        except Exception as e:
            logger.error(f"添加章节 {chapter['title']} 时出错: {e}")
    
    return added_chapters


def finalize_epub(book, toc, spine):
    """
    完成EPUB书籍的导航和目录设置
    
    Args:
        book: EPUB书籍对象
        toc: 目录列表
        spine: 书脊列表
    """
    # 添加导航
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # 设置书脊和目录
    book.spine = spine
    book.toc = toc


def write_epub_file(book, output_path):
    """
    将EPUB书籍写入文件
    
    Args:
        book: EPUB书籍对象
        output_path: 输出文件路径
        
    Returns:
        bool: 是否成功写入
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output_path), book, {})
        logger.info(f"已成功创建电子书：{output_path}")
        return True
    except Exception as e:
        logger.error(f"写入EPUB文件出错: {e}")
        return False


def merge_txt_to_epub(folder_path, output_path=None, author=None, novel_name=None, language='zh-CN'):
    """
    将文件夹中的txt文件合并为epub
    
    Args:
        folder_path: 包含txt文件的文件夹路径
        output_path: 输出epub文件的路径（可选）
        author: 作者名称（可选）
        novel_name: 小说名称（可选，如不指定则从文件名解析）
        language: 电子书语言代码
        
    Returns:
        str or None: 成功时返回输出路径，失败时返回None
    """
    folder_path = Path(folder_path)
    
    # 检查文件夹是否存在
    if not folder_path.exists() or not folder_path.is_dir():
        logger.error(f"文件夹不存在或不是有效目录: {folder_path}")
        return None
    
    # 获取所有txt文件
    txt_files = [f.name for f in folder_path.iterdir() if f.suffix.lower() == '.txt']
    if not txt_files:
        logger.error(f"在 {folder_path} 中没有找到TXT文件")
        return None
    
    logger.info(f"在 {folder_path} 中找到 {len(txt_files)} 个TXT文件")
    
    # 提取章节信息
    book_name, chapters = extract_chapters(txt_files, folder_path, novel_name)
    
    if not book_name:
        logger.error("无法确定小说名称")
        return None
    
    if not chapters:
        logger.error("未能提取任何有效章节")
        return None
    
    # 如果未指定输出路径，则使用小说名称作为文件名
    if not output_path:
        output_path = folder_path / f"{book_name}_脱水.epub"
    
    # 创建EPUB书籍
    book, epub_chapters, toc, spine = create_epub_book(book_name, chapters, author, language)
    
    # 添加章节
    added_count = add_chapters_to_book(book, chapters, epub_chapters, toc, spine)
    if added_count == 0:
        logger.error("未能添加任何章节到EPUB")
        return None
    
    # 完成EPUB设置
    finalize_epub(book, toc, spine)
    
    # 写入文件
    if write_epub_file(book, output_path):
        return str(output_path)
    else:
        return None


def main():
    """主函数，处理命令行参数并执行转换"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='将文件夹中的TXT文件合并为EPUB电子书')
    parser.add_argument('folder', help='包含TXT文件的文件夹路径')
    parser.add_argument('-o', '--output', help='输出EPUB文件的路径（可选）')
    parser.add_argument('-a', '--author', help='设置电子书的作者（可选）')
    parser.add_argument('-n', '--name', help='设置电子书的名称（可选，默认从文件名解析）')
    parser.add_argument('-l', '--language', default='zh-CN', help='设置电子书的语言（默认：zh-CN）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    parser.add_argument('-q', '--quiet', action='store_true', help='仅显示错误信息')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        setup_logger(logging.DEBUG)
    elif args.quiet:
        setup_logger(logging.ERROR)
    
    # 执行转换
    result = merge_txt_to_epub(args.folder, args.output, args.author, args.name, args.language)
    
    # 返回状态码
    if result:
        logger.info(f"转换完成！EPUB文件已保存到: {result}")
        return 0
    else:
        logger.error("转换失败！")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 