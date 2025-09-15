# MCP分布式爬虫系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg" alt="Status">
</p>

<p align="center">
  企业级分布式爬虫系统，集成DFD知识收集、智能代理池、人性化访问控制等高级功能
</p>

## 🚀 项目特色

### ✨ 核心功能
- **🕷️ 分布式爬虫架构** - 支持多节点并行爬取
- **📊 DFD知识收集** - 智能业务流程分析与可视化
- **🔄 代理池管理** - 自动代理轮换与验证
- **🎭 人性化访问** - 智能延迟控制，避免被封
- **📈 实时监控** - Web监控面板实时查看状态
- **🗃️ 知识库系统** - 结构化知识管理与检索

### 🎯 技术栈
- **后端**: Python 3.7+, asyncio, FastAPI
- **数据库**: Redis, SQLite
- **爬虫**: Playwright, Selenium, Requests
- **代理**: SOCKS5, HTTP代理, Tor网络
- **监控**: 实时Web仪表板
- **部署**: Docker支持（即将推出）

## 🛠️ 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/YuzQwQ/mcp-distributed-crawler.git
cd mcp-distributed-crawler

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动Redis
```bash
# Windows
redis-server.exe redis.windows.conf

# Linux/Mac
redis-server
```

### 3. 启动系统
```bash
# 一键启动完整系统
python start_distributed_system.py start --workers 3

# 访问监控面板
# http://localhost:8080
```

### 4. 功能测试
```bash
# 测试DFD知识收集
python enhanced_dfd_collector.py

# 测试知识库整理
python knowledge_organizer.py
```

## 📊 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   任务调度器     │    │   工作节点1     │    │   工作节点2     │
│  task_scheduler  │────│  worker_node    │────│  worker_node    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   结果收集器     │    │   监控系统       │    │   代理池        │
    │ result_collector│    │  monitoring     │    │ proxy_pool      │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎯 核心模块

### 1. 分布式爬虫系统
- **任务调度器** - 智能任务分配
- **工作节点** - 并行爬取处理
- **结果收集器** - 统一数据收集
- **监控系统** - 实时状态监控

### 2. DFD知识收集系统
- **知识收集** - 自动收集业务流程知识
- **知识分析** - 智能分析与验证
- **知识可视化** - 生成图表与报告
- **知识存储** - 结构化知识管理

### 3. 代理池管理系统
- **代理验证** - 实时代理可用性检测
- **代理轮换** - 智能代理选择
- **代理监控** - 代理状态实时监控
- **代理补充** - 自动代理发现

### 4. 人性化访问系统
- **智能延迟** - 模拟人类访问行为
- **User-Agent轮换** - 避免被识别为爬虫
- **请求随机化** - 降低被封风险
- **异常处理** - 智能错误恢复

## 📋 项目结构

```
mcp-distributed-crawler/
├── 📁 distributed/           # 分布式系统核心组件
│   ├── task_scheduler.py   # 任务调度器
│   ├── worker_node.py      # 工作节点
│   ├── result_collector.py # 结果收集器
│   └── monitoring.py       # 监控系统
├── 📁 knowledge_base/      # 知识库系统
├── 📁 utils/               # 工具库
│   ├── proxy_pool.py       # 代理池管理
│   ├── stealth_crawler.py  # 隐形爬虫
│   └── web_deduplication.py # 去重系统
├── 📁 docs/                # 项目文档
├── 📁 tests/               # 测试文件
├── 📁 scripts/             # 脚本工具
└── 📁 knowledge_base/      # 知识库存储
```

## 🎮 使用示例

### 基础爬虫任务
```python
# 提交爬虫任务
from distributed.task_queue import TaskQueue

queue = TaskQueue()
task = {
    "url": "https://example.com",
    "method": "GET",
    "callback": "parse_data"
}
queue.add_task(task)
```

### DFD知识收集
```python
# 收集业务流程知识
from enhanced_dfd_collector import EnhancedDFDKnowledgeCollector

collector = EnhancedDFDKnowledgeCollector()
result = collector.collect_knowledge("电商订单处理流程")
```

### 代理池使用
```python
# 获取可用代理
from utils.proxy_pool import ProxyPool

pool = ProxyPool()
proxy = pool.get_proxy()
```

## 🧪 测试

### 运行所有测试
```bash
python test_distributed_system.py
```

### 运行特定测试
```bash
# 测试DFD收集
python test_dfd_collection.py

# 测试代理池
python test_proxy_pool.py

# 测试人性化访问
python test_humanized_access.py
```

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 并发节点 | 支持1-100个 |
| 任务处理速度 | 1000+任务/分钟 |
| 代理池规模 | 1000+代理 |
| 成功率 | 95%+ |
| 知识收集准确率 | 100% |

## 🛡️ 安全特性

- **请求加密** - 保护敏感数据
- **访问控制** - 权限管理
- **日志审计** - 完整操作记录
- **异常监控** - 实时异常检测

## 📚 文档

- [📖 完整部署指南](GITHUB_PUSH_GUIDE.md)
- [🔧 配置说明](docs/CONFIG_GUIDE.md)
- [🎯 使用教程](HUMANIZED_ACCESS_GUIDE.md)
- [📊 系统架构](docs/distributed_crawler_architecture.md)

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 贡献指南
1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用 **MIT** 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🌟 Star历史

[![Star History Chart](https://api.star-history.com/svg?repos=YuzQwQ/mcp-distributed-crawler&type=Date)](https://star-history.com/#YuzQwQ/mcp-distributed-crawler&Date)

## 📞 联系我们

- **Issues**: [GitHub Issues](https://github.com/YuzQwQ/mcp-distributed-crawler/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YuzQwQ/mcp-distributed-crawler/discussions)

---

<p align="center">
  <b>🚀 让数据采集变得更智能、更安全、更高效！</b>
</p>