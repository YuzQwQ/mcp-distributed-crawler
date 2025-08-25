# 通用网页爬虫系统配置指南

## 概述

本系统支持通过配置文件自定义网页内容分析的行为，包括系统提示词、数据格式处理等。本指南详细说明了各种配置文件的格式和使用方法。

## 配置文件结构

```
config/
├── system_prompts.json     # 系统提示词配置
├── format_templates.json   # 数据格式模板配置
└── README.md              # 格式配置系统说明
```

## 1. 系统提示词配置 (system_prompts.json)

### 文件位置
`config/system_prompts.json`

### 配置结构

```json
{
  "format_name": "系统提示词配置",
  "description": "用于配置不同领域的网页内容分析系统提示词",
  "version": "1.0.0",
  "default_prompt_type": "general",
  "prompts": {
    "prompt_type_name": {
      "name": "提示词显示名称",
      "description": "提示词用途描述",
      "system_prompt": "具体的系统提示词内容"
    }
  },
  "usage_instructions": {
    "how_to_use": "使用说明",
    "available_types": ["可用的提示词类型列表"],
    "fallback": "回退机制说明"
  }
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `format_name` | string | 是 | 配置文件名称 |
| `description` | string | 是 | 配置文件描述 |
| `version` | string | 是 | 配置文件版本 |
| `default_prompt_type` | string | 是 | 默认使用的提示词类型 |
| `prompts` | object | 是 | 提示词定义集合 |
| `prompts.{type}.name` | string | 是 | 提示词显示名称 |
| `prompts.{type}.description` | string | 是 | 提示词用途描述 |
| `prompts.{type}.system_prompt` | string | 是 | 具体的系统提示词内容 |
| `usage_instructions` | object | 否 | 使用说明信息 |

### 内置提示词类型

| 类型 | 名称 | 适用场景 |
|------|------|----------|
| `general` | 通用网页内容分析 | 通用网页内容分析和总结 |
| `dfd` | 数据流图专业分析 | 数据流图相关内容分析 |
| `technical` | 技术文档分析 | 技术文档、API文档、编程教程 |
| `business` | 商业内容分析 | 商业资讯、市场分析、行业报告 |
| `academic` | 学术研究分析 | 学术论文、研究报告、科学文献 |
| `news` | 新闻资讯分析 | 新闻报道、时事评论、媒体资讯 |

### 自定义提示词

您可以在 `prompts` 对象中添加自定义的提示词类型：

```json
{
  "prompts": {
    "custom_type": {
      "name": "自定义分析类型",
      "description": "针对特定领域的内容分析",
      "system_prompt": "你是一位专业的...分析专家。请重点关注..."
    }
  }
}
```

## 2. 环境变量配置 (.env)

### 系统提示词配置

```bash
# 系统提示词配置
# 可选值: general, dfd, technical, business, academic, news, 或自定义类型
SYSTEM_PROMPT_TYPE=general
```

### 模型配置

```bash
# AI模型配置
MODEL=Qwen/Qwen3-30B-A3B
BASE_URL=https://api.siliconflow.cn/v1
OPENAI_API_KEY=your_api_key_here
VISUAL_MODEL=Pro/Qwen/Qwen2.5-VL-7B-Instruct
```

### Tor代理配置

```bash
# Tor代理配置（反爬虫功能）
USE_TOR=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=
TOR_EXECUTABLE_PATH=D:\develop\Tor Browser\Browser\TorBrowser\Tor\tor.exe
```

### 爬虫配置

```bash
# 爬虫配置
SCRAPER_COOKIES=
SERPAPI_API_KEY=your_serpapi_key_here
```

## 3. 使用方法

### 3.1 选择提示词类型

**方法一：通过环境变量**

在 `.env` 文件中设置：
```bash
SYSTEM_PROMPT_TYPE=technical
```

**方法二：通过代码参数**

在调用 `get_system_prompt()` 函数时传入参数：
```python
system_prompt = get_system_prompt("business")
```

### 3.2 添加新的提示词类型

1. 编辑 `config/system_prompts.json` 文件
2. 在 `prompts` 对象中添加新的提示词定义
3. 更新 `.env` 文件中的 `SYSTEM_PROMPT_TYPE` 值
4. 重启服务

### 3.3 修改现有提示词

1. 编辑 `config/system_prompts.json` 文件
2. 修改对应类型的 `system_prompt` 内容
3. 保存文件（无需重启服务，配置会动态加载）

## 4. 配置验证

### 4.1 配置文件格式验证

系统会在启动时自动验证配置文件格式，如果发现错误会在日志中输出警告信息。

### 4.2 回退机制

如果配置文件加载失败或指定的提示词类型不存在，系统会按以下顺序回退：

1. 使用 `default_prompt_type` 指定的默认类型
2. 使用配置文件中的第一个可用提示词
3. 使用硬编码的通用提示词

## 5. 最佳实践

### 5.1 提示词设计原则

1. **明确角色定位**：清楚定义AI助手的专业角色
2. **具体关注点**：列出需要重点关注的内容类型
3. **输出格式要求**：明确期望的输出格式和风格
4. **专业术语使用**：根据目标领域使用适当的专业术语

### 5.2 配置管理建议

1. **版本控制**：将配置文件纳入版本控制系统
2. **备份配置**：定期备份重要的配置文件
3. **测试验证**：修改配置后进行充分测试
4. **文档更新**：及时更新配置文档和说明

### 5.3 性能优化

1. **缓存机制**：系统会缓存加载的配置，避免重复读取
2. **配置大小**：保持配置文件大小合理，避免过长的提示词
3. **错误处理**：确保配置文件格式正确，避免解析错误

## 6. 故障排除

### 6.1 常见问题

**问题：配置文件加载失败**
- 检查文件路径是否正确
- 验证JSON格式是否有效
- 确认文件编码为UTF-8

**问题：提示词类型不存在**
- 检查 `SYSTEM_PROMPT_TYPE` 环境变量值
- 确认配置文件中存在对应的提示词定义
- 查看系统日志获取详细错误信息

**问题：提示词效果不佳**
- 调整提示词内容，增加更具体的指导
- 测试不同的提示词组合
- 根据实际输出结果优化提示词

### 6.2 日志查看

系统日志文件：`mcp_server.log`

关键日志信息：
- 配置文件加载状态
- 提示词类型选择过程
- 错误和警告信息

## 7. 示例配置

### 7.1 电商领域配置示例

```json
{
  "prompts": {
    "ecommerce": {
      "name": "电商内容分析",
      "description": "专门用于电商网站内容分析",
      "system_prompt": "你是一位专业的电商内容分析专家。请重点关注：\n1. 产品特性和卖点\n2. 价格策略和促销信息\n3. 用户评价和反馈\n4. 竞品对比分析\n5. 市场趋势和消费者需求\n6. 品牌定位和营销策略\n请用商业化的语言总结内容，突出商业价值和市场机会。"
    }
  }
}
```

### 7.2 医疗健康领域配置示例

```json
{
  "prompts": {
    "healthcare": {
      "name": "医疗健康内容分析",
      "description": "专门用于医疗健康相关内容分析",
      "system_prompt": "你是一位专业的医疗健康信息分析专家。请重点关注：\n1. 疾病症状和诊断信息\n2. 治疗方法和药物信息\n3. 预防措施和健康建议\n4. 医学研究和临床试验\n5. 医疗设备和技术进展\n6. 健康数据和统计信息\n请用专业但易懂的医学语言总结内容，确保信息的准确性和科学性。"
    }
  }
}
```

## 8. 更新日志

### v1.0.0 (当前版本)
- 初始版本发布
- 支持6种内置提示词类型
- 支持自定义提示词配置
- 支持环境变量和参数两种配置方式
- 完整的回退机制和错误处理

---

如有任何问题或建议，请查看系统日志或联系开发团队。