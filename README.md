# AI小说实验室(AINovelLab)

这是一个用Python开发的小说处理工具套件，集成了以下功能：

1. **EPUB分割器**：将EPUB电子书分割为单章TXT文件
2. **小说脱水工具**：使用AI自动将小说内容缩减至原文的30%-50%
3. **TXT合并转EPUB**：将TXT文件合并为EPUB电子书

## 版本信息

- 当前版本：v0.0.1 (release)
- 构建日期：2024-04-07
- 支持平台：Windows

## 快速开始

### 方法一：使用预编译的可执行文件

1. 下载最新版本的AINovelLab.zip
2. 解压至任意位置
3. 运行AINovelLab.exe

### 方法二：从源码运行

1. 克隆或下载本仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 运行程序：`python run.py`

## 基本使用

### 脱水处理流程

1. **EPUB转TXT**：使用EPUB分割器将电子书转换为TXT文件
2. **脱水处理**：对TXT文件进行AI内容压缩
3. **TXT转EPUB**：将处理后的TXT文件重新转换为EPUB格式

### API配置

本工具支持多种AI服务，包括：

- Google Gemini API
- OpenAI API（GPT系列模型）
- 其他兼容OpenAI接口的服务（如DeepSeek、Grok等）

**基本配置示例**：
```json
{
  "gemini_api": [
    {
      "key": "你的Gemini API密钥",
      "model": "gemini-2.0-flash",
      "rpm": 5
    }
  ],
  "openai_api": [
    {
      "key": "你的OpenAI API密钥",
      "model": "gpt-3.5-turbo",
      "rpm": 3
    }
  ],
  "max_rpm": 20,
  "preferred_api": "gemini"
}
```

> **详细API配置指南**：请参阅[API配置详细说明](doc/API_CONFIG.md)

## 优化提示

1. 小说脱水时，建议使用目录批量处理，可以配置多个API密钥提高效率
2. 使用EPUB分割器时，可以根据章节数量调整每个文件的章节数
3. 使用TXT转EPUB时，确保TXT文件按照"小说名_[序号]_章节名.txt"的格式命名
4. 已打包的可执行文件可以直接修改根目录下的`api_keys.json`文件来更新API配置

## 更多信息

- [详细API配置指南](doc/API_CONFIG.md) - 包含所有支持的API服务配置说明
- [项目结构说明](doc/PROJECT_STRUCTURE.md) - 包含代码结构和模块说明
- [打包说明](doc/BUILD_GUIDE.md) - 包含如何打包为可执行文件的说明

## 许可证

本项目采用MIT许可证 