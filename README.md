# AI小说实验室(AINovelLab)

这是一个用Python开发的小说处理工具套件，集成了以下功能：

1. **EPUB分割器**：将EPUB电子书分割为单章TXT文件
2. **小说脱水工具**：使用Gemini AI自动将小说内容缩减至原文的30%-50%
3. **TXT合并转EPUB**：将TXT文件合并为EPUB电子书

## 项目结构

```
AINovelLab/
├── src/                   # 源代码目录
│   ├── core/              # 核心功能模块
│   │   ├── epub_splitter.py    # EPUB分割器
│   │   ├── novel_condenser/    # 小说脱水工具(模块化)
│   │   │   ├── __init__.py       # 包初始化文件
│   │   │   ├── main.py           # 主模块
│   │   │   ├── api_service.py    # API服务
│   │   │   ├── file_utils.py     # 文件处理
│   │   │   ├── config.py         # 配置管理
│   │   │   ├── key_manager.py    # 密钥管理
│   │   │   └── stats.py          # 统计模块
│   │   ├── txt_to_epub.py      # TXT合并转EPUB工具
│   │   ├── api_manager.py      # API密钥管理
│   │   └── utils.py            # 通用工具函数
│   ├── gui/               # GUI相关代码
│   │   ├── main_window.py    # 主窗口
│   │   ├── home_tab.py       # 首页标签
│   │   ├── epub_splitter_tab.py # EPUB分割标签
│   │   ├── condenser_tab.py  # 脱水工具标签
│   │   ├── txt_to_epub_tab.py  # TXT转EPUB标签
│   │   └── worker.py         # 后台工作线程
│   ├── import_helper.py    # 导入路径设置辅助模块
│   └── main.py            # 主入口
├── config/                # 配置文件目录
│   ├── config.py          # 配置管理模块
│   ├── config_compat.py   # 配置兼容性处理
│   └── default_config.py  # 默认配置
├── api_keys.json          # API密钥配置文件(放在根目录方便打包后修改)
├── data/                  # 数据文件目录
├── resources/             # 资源文件
├── run.py                 # 项目入口脚本
└── README.md              # 项目说明文档
```

## 安装

### 环境要求

- Python 3.8+
- pip

### 安装步骤

1. 克隆或下载本仓库
2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方式

### 图形界面

启动图形界面有两种方式：

1. 通过项目根目录的入口脚本启动：

```bash
python run.py
```

2. 直接运行主程序文件：

```bash
python src/main.py
```

图形界面提供了直观的操作方式，集成了所有功能。

### 命令行

各功能模块也支持命令行方式使用：

#### EPUB分割器

```bash
python src/core/epub_splitter.py [epub文件路径] --output [输出目录] --chapters-per-file [每个文件的章节数]
```

#### 小说脱水工具

```bash
python src/novel_condenser.py [输入文件或目录] -o [输出目录] -c [配置文件]
```

#### TXT合并转EPUB

```bash
python src/core/txt_to_epub.py [TXT文件目录] --output [输出EPUB路径] --author [作者名]
```

## 配置Gemini API

小说脱水功能需要使用Google的Gemini API。你需要编辑项目根目录下的`api_keys.json`文件，添加你的API密钥。将配置文件放在根目录可以方便打包为exe后直接修改配置，不需要解包程序。

配置文件格式：

```json
{
  "gemini_api": [
    {
      "key": "你的API密钥",
      "model": "gemini-2.0-flash",
      "rpm": 5
    }
  ],
  "max_rpm": 20
}
```

## 项目结构说明

本项目采用模块化结构，将功能分为以下几个部分：

1. **核心功能模块**：`src/core/`目录中包含所有核心功能实现
2. **GUI界面模块**：`src/gui/`目录中包含所有图形界面相关代码
3. **配置模块**：`config/`目录中包含配置文件

项目使用统一的导入路径设置，简化了代码结构，避免了路径混乱的问题。

## 优化提示

1. 小说脱水时，建议使用目录批量处理，可以配置多个API密钥提高效率
2. 使用EPUB分割器时，可以根据章节数量调整每个文件的章节数
3. 使用TXT合并转EPUB时，确保TXT文件按照"小说名_[序号]_章节名.txt"的格式命名

## 许可证

本项目采用MIT许可证 