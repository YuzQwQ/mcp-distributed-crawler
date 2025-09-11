# 通用网页爬虫系统配置指南

本指南详细说明了通用网页爬虫系统的配置文件格式和使用方法。

## 配置文件概览

系统使用以下配置文件：
- `config/system_prompts.json` - 系统提示词配置
- `.env` - 环境变量配置
- `web_cache.db` - 网页去重缓存数据库（自动创建）

## 系统提示词配置 (config/system_prompts.json)

### 文件结构
```json
{
  "prompts": {
    "general": {
      "name": "通用网页内容分析",
      "description": "适用于各种类型网页的通用分析提示词",
      "content": "你是一个专业的网页内容分析助手..."
    },
    "dfd": {
      "name": "数据流图(DFD)专业分析",
      "description": "专门用于分析数据流图相关内容",
      "content": "你是数据流图(DFD)分析专家..."
    }
  }
}
```

### 字段说明
- `prompts`: 提示词集合对象
- `[type]`: 提示词类型标识符
  - `name`: 提示词显示名称
  - `description`: 提示词用途描述
  - `content`: 具体的提示词内容

### 内置提示词类型
- `general`: 通用网页内容分析（默认）
- `dfd`: 数据流图专业分析
- `technical`: 技术文档分析
- `business`: 商业内容分析
- `academic`: 学术研究分析
- `news`: 新闻资讯分析

### 自定义提示词
可以在 `prompts` 对象中添加新的提示词类型：
```json
{
  "prompts": {
    "custom_type": {
      "name": "自定义分析类型",
      "description": "针对特定领域的分析",
      "content": "你的自定义提示词内容..."
    }
  }
}
```

## 环境变量配置 (.env)

### 基础配置
```bash
# AI模型配置
OPENAI_API_KEY=your_openai_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini

# 系统提示词类型配置
SYSTEM_PROMPT_TYPE=general

# 网页去重配置
ENABLE_URL_DEDUP=true
ENABLE_CONTENT_DEDUP=true
URL_CACHE_DAYS=30
CONTENT_SIMILARITY_THRESHOLD=0.85
```

### 网页去重配置详解

#### ENABLE_URL_DEDUP
- **类型**: boolean (true/false)
- **默认值**: true
- **说明**: 是否启用URL去重功能
- **作用**: 防止重复抓取相同的URL

#### ENABLE_CONTENT_DEDUP
- **类型**: boolean (true/false)
- **默认值**: true
- **说明**: 是否启用内容去重功能
- **作用**: 检测并标记相似度过高的内容

#### URL_CACHE_DAYS
- **类型**: integer
- **默认值**: 30
- **范围**: 1-365
- **说明**: URL缓存保留天数
- **作用**: 超过指定天数的URL缓存将被自动清理

#### CONTENT_SIMILARITY_THRESHOLD
- **类型**: float
- **默认值**: 0.85
- **范围**: 0.0-1.0
- **说明**: 内容相似度阈值
- **作用**: 当两个内容的相似度超过此阈值时，认为是重复内容

### Tor代理配置（可选）
```bash
# Tor代理配置
USE_TOR=false
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_PASSWORD=your_tor_password
TOR_EXECUTABLE_PATH=tor
```

### 爬虫配置（可选）
```bash
# 爬虫配置
SCRAPER_COOKIES=your_cookies_here
SERPAPI_API_KEY=your_serpapi_key
```

## 使用方法

### 1. 配置系统提示词
1. 编辑 `config/system_prompts.json` 文件
2. 在 `.env` 文件中设置 `SYSTEM_PROMPT_TYPE` 为对应的类型
3. 重启服务使配置生效

### 2. 配置网页去重
1. 在 `.env` 文件中设置去重相关参数
2. 重启服务使配置生效
3. 使用 `manage_web_deduplication` 工具查看统计信息

### 3. 管理去重缓存
```python
# 查看去重统计
manage_web_deduplication(action="stats")

# 清理7天前的缓存
manage_web_deduplication(action="clean", days=7)

# 重置所有缓存
manage_web_deduplication(action="reset")
```

## 配置验证

### 系统提示词验证
- 检查 `config/system_prompts.json` 文件是否存在
- 验证JSON格式是否正确
- 确认指定的提示词类型是否存在

### 去重系统验证
- 检查 `web_cache.db` 数据库是否正常创建
- 验证去重配置参数是否在有效范围内
- 测试去重功能是否正常工作

## 最佳实践

### 提示词配置
1. **选择合适的提示词类型**：根据抓取内容的领域选择最匹配的提示词
2. **自定义提示词**：为特定项目创建专门的提示词类型
3. **定期更新**：根据使用效果调整和优化提示词内容

### 去重配置
1. **合理设置缓存时间**：根据内容更新频率调整 `URL_CACHE_DAYS`
2. **调整相似度阈值**：根据内容特点调整 `CONTENT_SIMILARITY_THRESHOLD`
3. **定期清理缓存**：避免缓存数据库过大影响性能
4. **监控去重效果**：定期查看去重统计信息

### 性能优化
1. **启用URL去重**：避免重复抓取，节省资源
2. **合理设置相似度阈值**：过低会误判，过高会漏检
3. **定期清理旧缓存**：保持数据库性能
4. **监控缓存大小**：避免磁盘空间不足

## 故障排除

### 常见问题

#### 1. 提示词加载失败
- **症状**: 使用默认通用提示词
- **原因**: 配置文件不存在或格式错误
- **解决**: 检查 `config/system_prompts.json` 文件

#### 2. 去重功能不工作
- **症状**: 重复抓取相同URL或内容
- **原因**: 去重功能被禁用或配置错误
- **解决**: 检查 `.env` 文件中的去重配置

#### 3. 缓存数据库错误
- **症状**: 去重功能异常或数据库锁定
- **原因**: 数据库文件损坏或权限问题
- **解决**: 删除 `web_cache.db` 文件重新创建

#### 4. 内存使用过高
- **症状**: 系统响应缓慢
- **原因**: 缓存数据过多
- **解决**: 清理旧缓存或降低缓存时间

### 日志查看
系统日志保存在 `mcp_server.log` 文件中，包含：
- 配置加载信息
- 去重检测结果
- 错误和警告信息

## 示例配置

### 学术研究项目配置
```bash
# .env
SYSTEM_PROMPT_TYPE=academic
ENABLE_URL_DEDUP=true
ENABLE_CONTENT_DEDUP=true
URL_CACHE_DAYS=60
CONTENT_SIMILARITY_THRESHOLD=0.90
```

### 新闻监控项目配置
```bash
# .env
SYSTEM_PROMPT_TYPE=news
ENABLE_URL_DEDUP=true
ENABLE_CONTENT_DEDUP=true
URL_CACHE_DAYS=7
CONTENT_SIMILARITY_THRESHOLD=0.80
```

### 技术文档收集配置
```bash
# .env
SYSTEM_PROMPT_TYPE=technical
ENABLE_URL_DEDUP=true
ENABLE_CONTENT_DEDUP=false
URL_CACHE_DAYS=90
```

## 更新日志

### v1.0.0
- 初始版本
- 支持系统提示词配置
- 实现网页去重系统
- 添加配置管理工具

---

如有问题或建议，请查看系统日志或联系开发团队。