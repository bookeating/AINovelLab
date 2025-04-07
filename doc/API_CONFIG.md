# AI小说实验室 API配置详细说明

本文档详细介绍了AI小说实验室支持的所有API服务配置方法。

## 目录

- [Gemini API配置](#gemini-api配置)
- [OpenAI API配置](#openai-api配置)
- [兼容OpenAI格式的其他LLM服务](#兼容openai格式的其他llm服务)
- [本地模型配置](#本地模型配置)
- [多API并行和服务切换](#多api并行和服务切换)

## Gemini API配置

### 获取API密钥

1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 注册/登录账号
3. 在左侧菜单中找到"API密钥"选项
4. 创建新的API密钥并复制

### 基本配置示例

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

### 多API密钥配置

为提高处理效率，你可以配置多个API密钥：

```json
{
  "gemini_api": [
    {
      "key": "你的第一个API密钥",
      "model": "gemini-2.0-flash",
      "rpm": 5
    },
    {
      "key": "你的第二个API密钥",
      "model": "gemini-1.5-flash",
      "rpm": 6
    },
    {
      "key": "你的第三个API密钥",
      "model": "gemini-2.0-pro",
      "rpm": 3
    }
  ],
  "max_rpm": 20
}
```

### 配置项说明

- `key`: 你的Gemini API密钥
- `model`: 使用的模型名称，推荐选项：
  - `gemini-2.0-flash` - 速度最快
  - `gemini-1.5-flash` - 平衡速度和质量
  - `gemini-2.0-pro` - 质量最好但速度较慢
- `rpm`: 每分钟请求次数限制（Rate Per Minute）
- `max_rpm`: 所有API密钥的总体最大RPM限制

## OpenAI API配置

### 获取API密钥

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册/登录账号
3. 在右上角个人头像下拉菜单中选择"View API keys"
4. 点击"Create new secret key"并复制生成的密钥

### 基本配置示例

```json
{
  "openai_api": [
    {
      "key": "你的OpenAI API密钥",
      "model": "gpt-3.5-turbo",
      "rpm": 3
    }
  ],
  "max_rpm": 20
}
```

### 完整配置示例（同时配置Gemini和OpenAI）

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
    },
    {
      "key": "你的第二个OpenAI API密钥",
      "model": "gpt-4",
      "rpm": 2
    }
  ],
  "max_rpm": 20,
  "preferred_api": "gemini"
}
```

### 配置项说明

- `key`: 你的OpenAI API密钥
- `model`: 使用的模型名称，主要选项：
  - `gpt-3.5-turbo` - 速度快，成本低
  - `gpt-4` - 质量高，成本高
- `rpm`: 每分钟请求次数限制（根据你的账户额度设置）
- `preferred_api`：首选API服务，可设置为`"gemini"`或`"openai"`

### 模型选择建议

- 对于普通文本处理：`gpt-3.5-turbo`速度较快，成本较低
- 对于质量要求高的处理：`gpt-4`质量更好，但成本较高
- OpenAI模型对中文处理的能力整体优于Gemini，但价格相对较高

> **费用提示**：使用OpenAI API会产生费用，请注意控制使用量，避免产生过高账单。

## 兼容OpenAI格式的其他LLM服务

本工具支持所有兼容OpenAI API格式的大语言模型服务，包括但不限于：

- DeepSeek
- Grok
- Claude (通过兼容层)
- Qwen (通义千问)
- GLM (智谱AI)
- 百度文心一言
- 阿里通义千问

### 配置示例

配置其他兼容OpenAI API的服务只需在`openai_api`部分添加相应配置：

```json
{
  "openai_api": [
    {
      "key": "你的API密钥",
      "model": "适用的模型名称",
      "rpm": 3,
      "base_url": "https://api.deepseek.com/v1",
      "provider": "deepseek"
    },
    {
      "key": "你的另一个API密钥",
      "model": "grok-1",
      "rpm": 2,
      "base_url": "https://api.grok.ai/v1",
      "provider": "grok"
    }
  ],
  "preferred_api": "openai"
}
```

### 配置项说明

- `base_url`: 服务提供商的API基础URL，必须指向兼容OpenAI API格式的端点
- `provider`: (可选) 服务提供商的标识，用于程序内部识别和日志记录
- `model`: 根据服务提供商支持的模型名称填写

### 常见服务商的模型和端点

| 服务商 | 模型示例 | 基础URL |
|-------|--------|---------|
| DeepSeek | deepseek-chat | https://api.deepseek.com/v1 |
| Grok | grok-1 | https://api.grok.ai/v1 |
| 智谱AI | glm-4 | https://api.chatglm.cn/v1 |
| 通义千问 | qwen-turbo, qwen-plus | https://dashscope.aliyuncs.com/api/v1 |
| Claude | claude-3-opus | https://api.anthropic.com/v1 |

## 本地模型配置

### 使用LM Studio

```json
{
  "openai_api": [
    {
      "key": "无需真实密钥",
      "model": "你部署的模型名称",
      "rpm": 1,
      "base_url": "http://localhost:1234/v1",
      "provider": "local" 
    }
  ],
  "preferred_api": "openai"
}
```

### 使用Ollama

```json
{
  "openai_api": [
    {
      "key": "ollama",
      "model": "llama3",
      "rpm": 1,
      "base_url": "http://localhost:11434/v1",
      "provider": "ollama" 
    }
  ],
  "preferred_api": "openai"
}
```

## 多API并行和服务切换

程序会根据以下逻辑智能地在不同API服务之间切换：

1. 优先使用`preferred_api`指定的服务
2. 在同一类API中，按照配置顺序轮流使用不同密钥
3. 当某个API服务不可用或达到配额限制时，自动切换到另一种服务
4. 如果你同时配置了Gemini和多种OpenAI兼容服务，程序会优先考虑`preferred_api`的设置

### 高级配置示例

同时使用多种API服务，最大化处理效率：

```json
{
  "gemini_api": [
    {
      "key": "你的Gemini API密钥-1",
      "model": "gemini-2.0-flash",
      "rpm": 5
    },
    {
      "key": "你的Gemini API密钥-2",
      "model": "gemini-2.0-flash",
      "rpm": 5
    }
  ],
  "openai_api": [
    {
      "key": "你的OpenAI API密钥",
      "model": "gpt-3.5-turbo",
      "rpm": 3
    },
    {
      "key": "你的DeepSeek API密钥",
      "model": "deepseek-chat",
      "rpm": 10,
      "base_url": "https://api.deepseek.com/v1",
      "provider": "deepseek"
    },
    {
      "key": "无需真实密钥",
      "model": "llama3",
      "rpm": 2,
      "base_url": "http://localhost:1234/v1",
      "provider": "local"
    }
  ],
  "max_rpm": 30,
  "preferred_api": "openai"
}
```

> **提示**：配置多种API服务可以同时提高处理速度和容错性，当某个服务不可用时，程序会自动切换到其他可用服务。 