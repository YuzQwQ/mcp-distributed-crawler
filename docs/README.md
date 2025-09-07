# 🕷️ 通用网页爬虫系统

一个功能强大的通用网页内容爬取与分析系统，基于MCP（Model Context Protocol）构建，支持各种网页内容的智能抓取、分析和结构化存储。

## ✨ 功能特点

- **🌐 通用性强**: 支持各种类型网站和内容的爬取分析
- **🔍 智能搜索**: 支持关键词搜索和批量内容发现
- **📊 内容解析**: 智能提取文本、链接、图片、表格等各类内容元素
- **🤖 AI分析**: 使用先进AI模型进行内容理解和结构化处理
- **📋 多格式输出**: 生成JSON、Markdown等多种格式的结构化数据
- **🛡️ 反爬虫对抗**: 集成Tor代理和多种反爬虫策略
- **⚡ 高效处理**: 支持大规模网页的批量抓取和并发处理
- **💾 灵活存储**: 支持自定义数据格式和存储方案

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境变量配置

在项目根目录创建`.env`文件，添加以下配置：

```
# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key
BASE_URL=https://api.openai.com/v1  # 或其他API端点
MODEL=gpt-4  # 或其他模型

# 视觉模型配置
VISUAL_API_URL=https://api.siliconflow.cn/v1/chat/completions  # 或其他API端点
VISUAL_MODEL=Pro/Qwen/Qwen2.5-VL-7B-Instruct  # 视觉模型名称

# 搜索API配置
SERPAPI_API_KEY=your_serpapi_api_key

# Tor代理配置（反爬虫）
USE_TOR=false  # 设置为true启用Tor代理
TOR_SOCKS_PORT=9050  # Tor SOCKS代理端口
TOR_CONTROL_PORT=9051  # Tor控制端口
TOR_PASSWORD=  # Tor控制密码（可选）
TOR_EXECUTABLE_PATH=tor  # Tor可执行文件路径
```

## Tor代理反爬虫配置

本系统支持使用Tor代理来对抗网站的反爬虫机制，通过动态更换IP地址来提高爬取成功率。

### 安装Tor

**Windows:**
1. 下载Tor Browser或Tor Expert Bundle
2. 将tor.exe添加到系统PATH，或在.env中指定完整路径

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt-get install tor

# macOS
brew install tor
```

### 启用Tor代理

1. 在`.env`文件中设置：
   ```
   USE_TOR=true
   ```

2. 可选配置项：
   ```
   TOR_SOCKS_PORT=9050  # SOCKS代理端口
   TOR_CONTROL_PORT=9051  # 控制端口
   TOR_PASSWORD=your_password  # 控制密码（可选）
   TOR_EXECUTABLE_PATH=/path/to/tor  # Tor可执行文件路径
   ```

### Tor代理功能

系统提供以下Tor管理功能：

- `start_tor_proxy()` - 启动Tor代理服务
- `stop_tor_proxy()` - 停止Tor代理服务
- `change_tor_identity()` - 更换IP地址（获取新身份）
- `get_tor_status()` - 查看Tor代理状态

### 使用建议

1. **自动启动**: 启用Tor后，系统会在启动时自动启动Tor代理
2. **IP轮换**: 遇到反爬虫时，可以调用`change_tor_identity()`更换IP
3. **性能考虑**: Tor代理会降低访问速度，建议根据需要启用
4. **合规使用**: 请遵守目标网站的robots.txt和使用条款

## 📋 数据输出格式说明

系统支持多种结构化数据输出格式，可根据需要自定义字段和结构：

### 标准JSON格式
```json
{
  "title": "网页标题",
  "url": "原始网页URL",
  "content": {
    "summary": "AI生成的内容摘要",
    "main_text": "主要文本内容",
    "keywords": ["关键词1", "关键词2"],
    "links": ["相关链接1", "相关链接2"],
    "images": ["图片URL1", "图片URL2"]
  },
  "metadata": {
    "crawl_time": "抓取时间戳",
    "content_type": "内容类型",
    "language": "内容语言",
    "word_count": "字数统计",
    "domain": "网站域名"
  },
  "analysis": {
    "topic": "主题分类",
    "sentiment": "情感分析",
    "quality_score": "内容质量评分",
    "relevance": "相关性评分"
  }
}
```

### 字段说明：

- **title**: 网页标题
- **url**: 原始网页链接
- **content**: 提取的主要内容信息
- **metadata**: 爬取过程和网页的元数据信息
- **analysis**: AI分析结果，包括主题分类、情感分析等

## 运行

```bash
python server.py
```

## 使用客户端连接

```bash
python client.py server.py
```

## 使用示例

### 1. 技术文档收集
```
搜索 "Python爬虫教程和最佳实践"
```

### 2. 市场调研分析
```
搜索 "人工智能行业发展趋势报告"
```

### 3. 新闻资讯监控
```
搜索 "区块链技术最新动态"
```

### 4. 网页内容分析
```
分析这个网页的内容：https://example.com/article
```

### 5. 竞品信息收集
```
帮我搜索"电商平台用户体验设计案例"
```

### 6. 学术资料整理
```
搜索 "机器学习算法研究论文"
```

### 7. 社交媒体分析
```
分析这个社交媒体页面：https://twitter.com/example
```

## 🎯 适用场景

- **📚 学术研究**: 收集和整理学术论文、技术文档
- **📊 市场调研**: 分析竞品信息、行业报告
- **📰 新闻监控**: 追踪特定主题的新闻动态
- **💼 商业分析**: 收集企业信息、产品数据
- **🔍 内容发现**: 发现和整理优质内容资源
- **📈 数据收集**: 获取价格、评论等结构化数据
