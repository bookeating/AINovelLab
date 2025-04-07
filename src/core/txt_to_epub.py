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
import uuid  # 添加uuid模块导入
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
    # 标准格式：小说名称_[序号]_章节名称.txt
    pattern = r"(.+?)_\[(\d+)\]_(.+?)\.txt$"
    match = re.match(pattern, filename)
    if match:
        novel_name = match.group(1)
        chapter_number = int(match.group(2))
        chapter_title = match.group(3)
        
        # 如果章节标题是"目录"，标记为特殊序号
        if chapter_title == "目录":
            logger.info(f"检测到目录文件: {filename}")
            chapter_number = -1  # 使用负数使目录排在最前面，但不作为正式章节
            
        return novel_name, chapter_number, chapter_title
    
    # 尝试其他可能的格式: 小说名_[开始-结束].txt，用于处理多章节合并文件
    pattern2 = r"(.+?)_\[(\d+)-(\d+)\]\.txt$"
    match = re.match(pattern2, filename)
    if match:
        novel_name = match.group(1)
        start_chapter = int(match.group(2))
        chapter_title = f"第{start_chapter}章"
        return novel_name, start_chapter, chapter_title
    
    # 尝试更宽松的格式：小说名称_序号_章节名称.txt（没有方括号）
    pattern3 = r"(.+?)_(\d+)_(.+?)\.txt$"
    match = re.match(pattern3, filename)
    if match:
        novel_name = match.group(1)
        chapter_number = int(match.group(2))
        chapter_title = match.group(3)
        return novel_name, chapter_number, chapter_title
        
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
    # 确保内容不为空
    if not content or not content.strip():
        logger.warning(f"章节 '{chapter_title}' 内容为空，将添加提示文本")
        content = "(此章节内容为空)"
    
    # 转义章节标题中的特殊字符
    chapter_title = chapter_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    
    # 不使用BeautifulSoup，直接构建HTML
    html = '<?xml version="1.0" encoding="utf-8"?>\n'
    html += '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
    html += '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">\n'
    html += '<head>\n'
    html += f'<title>{chapter_title}</title>\n'
    html += '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
    html += '</head>\n'
    html += '<body>\n'
    
    # 添加章节标题
    html += f'<h1>{chapter_title}</h1>\n'
    
    # 将内容分段并添加
    paragraphs = content.split('\n')
    for p_text in paragraphs:
        if p_text.strip():
            # 转义HTML特殊字符
            p_text = p_text.strip()
            p_text = p_text.replace('&', '&amp;')
            p_text = p_text.replace('<', '&lt;')
            p_text = p_text.replace('>', '&gt;')
            p_text = p_text.replace('"', '&quot;')
            html += f'<p>{p_text}</p>\n'
    
    html += '</body>\n'
    html += '</html>'
    
    return html


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
        if name and number is not None and title:
            # 跳过目录文件（序号为负数的文件，如-1）
            if number < 0:
                logger.info(f"跳过目录文件: {filename}")
                continue
                
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
    
    # 如果没有有效章节，返回错误
    if not chapters:
        logger.error("未能提取任何有效章节，请检查文件命名格式")
        return final_novel_name, []
        
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
    
    if not chapters:
        logger.error("没有章节可添加")
        return 0
    
    # 添加默认CSS样式
    default_css = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content="""
        body { font-family: serif; }
        h1 { text-align: center; margin: 1em 0; }
        p { text-indent: 2em; margin: 0.5em 0; line-height: 1.5; }
        """
    )
    book.add_item(default_css)
    
    # 添加封面页
    book_title = book.title
    book_author = "未知作者"
    if hasattr(book, 'metadata') and 'creator' in book.metadata:
        if book.metadata['creator']:
            book_author = book.metadata['creator'][0][0]
    
    cover_html = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">
<head>
  <title>封面</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <style type="text/css">
    body {{ margin: 0; padding: 0; text-align: center; }}
    .cover {{ margin: 0 auto; padding: 1em; max-width: 100%; }}
    h1 {{ font-size: 2em; margin: 1em 0; }}
    .author {{ font-size: 1.2em; margin: 1em 0; }}
  </style>
</head>
<body>
  <div class="cover">
    <h1>{book_title}</h1>
    <p class="author">{book_author}</p>
  </div>
</body>
</html>'''
    
    cover = epub.EpubHtml(
        title='封面',
        file_name='cover.xhtml',
        lang='zh-CN',
        content=cover_html
    )
    book.add_item(cover)
    epub_chapters.append(cover)
    toc.append(epub.Link('cover.xhtml', '封面', 'cover'))
    spine.append(cover)
    
    # 创建目录页
    toc_html = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">
<head>
  <title>目录</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <style type="text/css">
    body {{ margin: 1em; padding: 0; }}
    h1 {{ text-align: center; margin: 1em 0; }}
    .toc {{ margin: 1em 0; }}
    .toc a {{ text-decoration: none; color: #333; }}
    .toc a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>目录</h1>
  <div class="toc">
'''
    
    for i, chapter in enumerate(chapters):
        # 转义特殊字符
        safe_title = chapter["title"].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        toc_html += f'    <p><a href="chapter_{chapter["number"]}.xhtml">{safe_title}</a></p>\n'
    
    toc_html += '''  </div>
</body>
</html>'''
    
    toc_page = epub.EpubHtml(
        title='目录',
        file_name='toc.xhtml',
        lang='zh-CN',
        content=toc_html
    )
    book.add_item(toc_page)
    epub_chapters.append(toc_page)
    toc.append(epub.Link('toc.xhtml', '目录', 'toc'))
    spine.append(toc_page)
    
    # 添加常规章节
    for chapter in chapters:
        try:
            # 读取章节内容
            content = read_txt_content(chapter['path'])
            if not content or not content.strip():
                logger.warning(f"章节 {chapter['title']} 内容为空，将添加默认内容")
                content = f"(此章节内容为空)"
            
            # 创建epub章节
            chapter_id = f"chapter_{chapter['number']}"
            file_name = f"{chapter_id}.xhtml"
            
            # 设置章节内容
            html_content = create_chapter_html(chapter['title'], content)
            
            # 创建章节对象
            epub_chapter = epub.EpubHtml(
                title=chapter['title'],
                file_name=file_name,
                content=html_content,
                lang='zh-CN'
            )
            
            # 不在这里添加CSS引用，避免可能的问题
            # epub_chapter.add_item(default_css)
            
            # 添加到书籍
            book.add_item(epub_chapter)
            epub_chapters.append(epub_chapter)
            toc.append(epub.Link(file_name, chapter['title'], chapter_id))
            spine.append(epub_chapter)
            
            added_chapters += 1
            logger.debug(f"已添加章节 {chapter['number']}: {chapter['title']}")
            
        except Exception as e:
            logger.error(f"添加章节 {chapter['title']} 时出错: {e}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")
    
    # 确保至少添加了一个章节
    if added_chapters == 0:
        logger.error("没有任何章节被成功添加到EPUB，请检查文件内容")
    else:
        logger.info(f"成功添加 {added_chapters} 个章节")
    
    return added_chapters


def finalize_epub(book, toc, spine):
    """
    完成EPUB书籍的导航和目录设置
    
    Args:
        book: EPUB书籍对象
        toc: 目录列表
        spine: 书脊列表
    """
    try:
        # 添加导航文件
        book.add_item(epub.EpubNcx())
        
        # 创建自定义的导航内容
        nav_content = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">
<head>
  <title>导航</title>
  <meta charset="utf-8" />
</head>
<body>
  <nav id="toc" epub:type="toc">
    <h1>目录</h1>
    <ol>
'''
        
        # 添加封面和目录
        nav_content += '      <li><a href="cover.xhtml">封面</a></li>\n'
        nav_content += '      <li><a href="toc.xhtml">目录</a></li>\n'
        
        # 添加各章节到导航
        for item in book.spine:
            if item == 'nav':
                continue
                
            if hasattr(item, 'title') and hasattr(item, 'file_name'):
                if not (item.file_name == 'cover.xhtml' or item.file_name == 'toc.xhtml'):
                    # 转义特殊字符
                    safe_title = item.title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                    nav_content += f'      <li><a href="{item.file_name}">{safe_title}</a></li>\n'
        
        nav_content += '''    </ol>
  </nav>
</body>
</html>'''
        
        # 创建自定义导航
        nav = epub.EpubHtml(
            uid='nav',
            file_name='nav.xhtml',
            title='导航',
            content=nav_content
        )
        nav.add_link(href='style/default.css', rel='stylesheet', type='text/css')
        nav.properties = ['nav']
        book.add_item(nav)
        
        # 确保spine中包含'nav'
        if 'nav' not in spine:
            spine.append('nav')
        
        # 设置书脊和目录
        book.spine = spine
        book.toc = toc
        
        # 添加额外的元数据
        book.add_metadata('DC', 'description', '由TXT转EPUB工具生成')
        book.add_metadata('DC', 'publisher', 'AI小说实验室')
        book.add_metadata('DC', 'source', 'TXT文件转换')
        book.add_metadata('DC', 'rights', '版权归原作者所有')
        
        # 使用正确的uuid模块
        unique_id = str(uuid.uuid4())
        book.add_metadata('DC', 'identifier', f'uuid:{unique_id}', {'id': 'pub-id'})
        
        logger.info("EPUB结构配置完成")
    except Exception as e:
        logger.error(f"配置EPUB结构时出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")


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
        # 检查book对象是否有效
        if not book or not hasattr(book, 'spine') or not book.spine:
            logger.error("无效的EPUB书籍对象: spine为空")
            return False
            
        # 检查书籍是否有实际内容章节
        content_items = [item for item in book.spine if item != 'nav']
        if not content_items:
            logger.error("EPUB书籍没有内容章节")
            return False
            
        # 打印调试信息
        logger.info(f"EPUB书籍信息: 标题={book.title}, 章节数={len(content_items)}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入前清理已存在的同名文件
        if output_path.exists():
            logger.warning(f"文件已存在，将被覆盖: {output_path}")
            try:
                output_path.unlink()
            except Exception as e:
                logger.warning(f"无法删除现有文件: {e}")
        
        logger.info(f"正在写入EPUB文件: {output_path}")
        
        # 使用更兼容的选项
        options = {
            'epub2_guide': True,  # 启用EPUB2指南
            'epub3_landmark': False,  # 禁用EPUB3地标
            'epub3_pages': False,  # 禁用EPUB3页面
            'landmark_title': 'Guide',  # 指南标题
            'spine_direction': None  # 不设置脊柱方向
        }
        
        # 直接写入，不要使用复杂的捕获异常和备用策略
        epub.write_epub(str(output_path), book, options)
        
        # 验证文件是否成功写入且大小合理
        if output_path.exists() and output_path.stat().st_size > 1000:  # 至少1KB
            logger.info(f"已成功创建电子书：{output_path}")
            return True
        else:
            logger.error(f"生成的EPUB文件过小或不存在: {output_path}")
            return False
    except Exception as e:
        logger.error(f"写入EPUB文件出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
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
    try:
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
        
        # 创建一个简单的EPUB书籍
        book = epub.EpubBook()
        book.set_title(book_name)
        book.set_language(language)
        
        if author:
            book.add_author(author)
        else:
            book.add_author("佚名")  # 默认作者
        
        # 添加CSS
        style = '''
        body { 
            font-family: "Noto Serif CJK SC", "Source Han Serif CN", SimSun, serif; 
            margin: 5%; 
            line-height: 1.5;
        }
        h1 { 
            text-align: center;
            font-size: 1.5em;
            margin: 1em 0;
        }
        h2 { 
            text-align: center;
            font-size: 1.2em;
            margin: 0.8em 0;
        }
        p { 
            text-indent: 2em; 
            margin: 0.3em 0;
        }
        .cover {
            text-align: center;
            margin: 3em 0;
        }
        .author {
            text-align: center;
            margin: 1em 0;
        }
        '''
        css = epub.EpubItem(uid="style", 
                           file_name="style.css", 
                           media_type="text/css", 
                           content=style)
        book.add_item(css)
        
        # 添加封面页
        cover_title = f'<h1 class="cover">{book_name}</h1>'
        cover_author = f'<p class="author">作者：{author if author else "佚名"}</p>'
        
        cover = epub.EpubHtml(title='封面', 
                             file_name='cover.xhtml',
                             lang=language)
        cover.content = f'''
        <html>
        <head>
            <title>封面</title>
            <link rel="stylesheet" href="style.css" type="text/css" />
        </head>
        <body>
            <div class="cover">
                {cover_title}
                {cover_author}
            </div>
        </body>
        </html>
        '''
        book.add_item(cover)
        
        # 添加目录页
        toc_content = '<h1>目录</h1>\n<div class="toc">'
        for i, chapter in enumerate(chapters):
            safe_title = chapter["title"].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            toc_content += f'<p><a href="chapter_{i+1}.xhtml">{safe_title}</a></p>\n'
        toc_content += '</div>'
        
        toc_page = epub.EpubHtml(title='目录',
                                file_name='toc.xhtml',
                                lang=language)
        toc_page.content = f'''
        <html>
        <head>
            <title>目录</title>
            <link rel="stylesheet" href="style.css" type="text/css" />
        </head>
        <body>
            {toc_content}
        </body>
        </html>
        '''
        book.add_item(toc_page)
        
        # 添加章节
        epub_chapters = []
        for i, chapter in enumerate(chapters):
            content = read_txt_content(chapter['path'])
            if not content.strip():
                content = "(此章节内容为空)"
            
            # 转义内容，确保安全
            safe_title = chapter['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            
            # 构建段落HTML
            paragraphs_html = ""
            for p in content.split('\n'):
                if p.strip():
                    p_safe = p.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                    paragraphs_html += f'<p>{p_safe}</p>\n'
            
            # 创建章节
            c = epub.EpubHtml(title=safe_title, 
                             file_name=f'chapter_{i+1}.xhtml',
                             lang=language)
            
            c.content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{language}">
<head>
    <title>{safe_title}</title>
    <link rel="stylesheet" href="style.css" type="text/css" />
    <meta charset="utf-8" />
</head>
<body>
    <h1>{safe_title}</h1>
    {paragraphs_html}
</body>
</html>
            '''
            
            book.add_item(c)
            epub_chapters.append(c)
        
        # 添加导航
        book.add_item(epub.EpubNcx())
        nav = epub.EpubNav()
        book.add_item(nav)
        
        # 设置书籍脊柱（阅读顺序）
        book.spine = ['cover', 'nav', 'toc'] + [f'chapter_{i+1}' for i in range(len(epub_chapters))]
        
        # 设置目录
        book.toc = [epub.Section('封面', [cover]),
                   epub.Section('目录', [toc_page])] + epub_chapters
        
        # 添加元数据
        book.add_metadata('DC', 'description', f'{book_name} - 由AI小说实验室生成')
        book.add_metadata('DC', 'publisher', 'AI小说实验室')
        book.add_metadata('DC', 'rights', '版权归原作者所有')
        book.add_metadata('DC', 'identifier', f'uuid:{str(uuid.uuid4())}', {'id': 'unique-id'})
        
        # 写入文件
        if write_epub_file(book, output_path):
            return str(output_path)
        else:
            return None
    except Exception as e:
        logger.error(f"合并TXT文件时出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
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