# 网页搜索与抓取工具

这个项目提供了一个强大的网页搜索与内容抓取工具，使用SerpAPI搜索引擎和MySQL数据库存储结果。

## 功能特点

- 使用SerpAPI支持多种搜索引擎（Google、Bing、百度等）
- 支持网页内容抓取和分析
- 使用视觉模型分析网页中的图片
- 将抓取结果存储到MySQL数据库
- 支持查询已存储的网页摘要

## 安装依赖

```bash
pip install -r requirements.txt
```

## 数据库设置

1. 确保已安装MySQL服务器
2. 创建一个新的数据库：
   ```sql
   CREATE DATABASE web_scraper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. 创建一个MySQL用户并授予权限（或使用现有用户）
4. 在`.env`文件中配置数据库连接信息：
   ```
   # MySQL数据库配置
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=your_username
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=web_scraper
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

# 天气API配置
HEFENG_API_KEY=your_hefeng_api_key
HEFENG_API_HOST=api.qweather.com
AMAP_API_KEY=your_amap_api_key

# 搜索API配置
SERPAPI_API_KEY=your_serpapi_api_key

# MySQL数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=web_scraper
```

## 运行

```bash
python server.py
```

## 使用客户端连接

```bash
python client.py server.py
```
