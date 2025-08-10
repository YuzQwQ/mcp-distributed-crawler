# 📊 DFD知识库构建系统

一个专业的数据流图(DFD)知识收集与分析系统，基于MCP（Model Context Protocol）构建，专门用于搜索、抓取和整理DFD绘制相关的专业知识。

## ✨ 功能特点

- **🎯 DFD专业化**: 专门针对数据流图绘制知识进行收集和分析
- **🔍 智能搜索**: 使用DFD专业关键词扩展搜索，提高相关性
- **📚 知识提取**: 自动识别和提取DFD四大核心元素相关内容
- **🤖 专家级分析**: AI模型专门训练用于DFD知识分析和总结
- **📊 结构化输出**: 生成符合DFD知识库标准的结构化JSON数据
- **🛡️ 高效采集**: 集成Tor代理和反爬虫机制，确保稳定采集
- **⚡ 批量处理**: 支持大规模DFD相关网页的批量抓取和分析
- **💾 标准存储**: 自动生成JSON和Markdown格式的专业知识库

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

## 📋 DFD结构化数据格式说明

系统现在生成符合DFD知识库新要求的结构化JSON格式，包含以下结构：

```json
{
  "level": 0,
  "functions": [
    "用户管理",
    "数据处理", 
    "信息查询",
    "报告生成"
  ],
  "entities": [
    "用户",
    "管理员",
    "外部系统"
  ],
  "data_stores": [
    "用户数据库",
    "系统配置文件",
    "日志记录"
  ],
  "metadata": {
    "source_url": "原始网页URL",
    "source_title": "网页标题",
    "crawl_time": "抓取时间戳",
    "content_summary": "AI生成的内容摘要",
    "tech_topic": "技术主题",
    "dfd_description": "基于网页内容自动生成的Level 0数据流图结构"
  }
}
```

### 字段说明：

- **level**: DFD图的层次级别（0表示Level 0 DFD上下文图）
- **functions**: 系统内部的主要处理功能或业务流程（用圆形表示）
- **entities**: 与系统交互的外部人员、组织或系统（用矩形表示）
- **data_stores**: 系统中存储数据的容器或数据库（用平行线表示）
- **metadata**: 包含数据来源和描述信息的元数据

## 运行

```bash
python server.py
```

## 使用客户端连接

```bash
python client.py server.py
```

## 使用示例

### 1. DFD基础知识收集
```
搜索 "数据流图基本概念和四大元素"
```

### 2. DFD绘制方法学习
```
搜索 "DFD绘制步骤和层次分解方法"
```

### 3. DFD工具和规范研究
```
搜索 "数据流图绘制工具和符号规范"
```

### 4. 分析专业DFD教程
```
分析这个DFD教程：https://example.com/dfd-tutorial
```

### 5. 收集DFD案例研究
```
帮我搜索"系统分析中数据流图实际应用案例"
```
