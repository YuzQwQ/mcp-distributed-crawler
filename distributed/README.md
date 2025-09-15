# 分布式爬虫系统

基于Stealth爬虫的高性能分布式爬虫系统，支持大规模并发爬取、智能调度、故障恢复和实时监控。

## 系统架构

### 核心组件

1. **任务队列系统** (`task_queue.py`)
   - 基于Redis的分布式任务队列
   - 支持任务优先级、去重、持久化
   - 可靠的消息传递机制

2. **工作节点** (`worker_node.py`)
   - 任务消费和爬虫执行
   - 状态上报和故障恢复
   - 动态扩缩容支持

3. **任务调度器** (`task_scheduler.py`)
   - 智能任务分发算法
   - 负载均衡和节点监控
   - 动态扩缩容决策

4. **结果收集器** (`result_collector.py`)
   - 数据聚合和存储管理
   - 实时统计和导出功能
   - 支持多种存储后端

5. **监控系统** (`monitoring.py`)
   - 性能指标收集
   - 健康检查和告警机制
   - Web可视化面板

6. **配置管理** (`config.py`)
   - 集中配置管理
   - 动态更新和环境隔离
   - 版本控制支持

### 技术特性

- **高性能**: 基于asyncio的异步IO，支持数千并发连接
- **高可靠**: 完善的故障检测和自动恢复机制
- **可扩展**: 水平扩展，支持动态添加工作节点
- **易监控**: 实时性能监控和可视化面板
- **容错性**: 节点故障自动转移，任务不丢失
- **人性化访问**: 智能延迟控制，防止对目标网站造成过大压力
- **域名感知**: 针对不同域名独立控制访问频率

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

创建 `.env` 文件：

```bash
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# MongoDB配置
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=distributed_crawler

# 监控配置
MONITORING_HOST=0.0.0.0
MONITORING_PORT=8080
```

### 3. 启动系统

#### 启动监控系统
```bash
python monitoring.py
```

#### 启动任务调度器
```bash
python task_scheduler.py
```

#### 启动工作节点
```bash
python worker_node.py --node-id worker-1
```

#### 启动结果收集器
```bash
python result_collector.py
```

### 4. 提交任务

```python
from task_queue import TaskQueue, CrawlerTask

queue = TaskQueue()
task = CrawlerTask(
    url="https://example.com",
    callback="parse_page",
    priority=1
)
queue.enqueue(task)
```

## 系统测试

运行完整测试套件：

```bash
python test_system.py
```

## 性能指标

- **任务吞吐量**: 支持10,000+任务/秒
- **并发连接**: 支持5,000+并发连接
- **节点规模**: 支持100+工作节点
- **故障恢复**: 99.9%可用性，故障恢复时间<30秒

## 监控面板

访问 http://localhost:8080 查看实时监控面板：

- 系统概览：任务队列状态、工作节点健康度
- 性能指标：吞吐量、延迟、错误率
- 资源使用：CPU、内存、网络
- 告警信息：实时告警和历史记录

## 部署方案

### 单机部署
适合开发和测试环境，所有组件运行在同一台机器上。

### 集群部署
生产环境推荐：
- Redis集群：3主3从
- MongoDB分片集群
- 工作节点：按需动态扩展
- 负载均衡：Nginx + HAProxy

## 故障处理

### 工作节点故障
- 自动检测节点心跳超时
- 任务重新分配到健康节点
- 故障节点自动重启

### Redis故障
- 主从切换
- 任务队列持久化恢复
- 客户端重连机制

### 网络分区
- 脑裂检测和处理
- 任务幂等性保证
- 数据一致性校验

## 扩展开发

### 添加新的爬虫类型

1. 创建爬虫类继承自 `BaseCrawler`
2. 实现 `parse` 方法
3. 注册到工作节点

```python
from worker_node import BaseCrawler

class MyCrawler(BaseCrawler):
    async def parse(self, task):
        # 实现爬虫逻辑
        pass
```

### 添加新的存储后端

1. 实现 `StorageBackend` 接口
2. 注册到结果收集器

```python
from result_collector import StorageBackend

class MyStorage(StorageBackend):
    async def store(self, result):
        # 实现存储逻辑
        pass
```

## 配置示例

### 生产环境配置

```yaml
# config/production.yaml
redis:
  host: redis-cluster
  port: 6379
  db: 0
  max_connections: 100

mongodb:
  uri: mongodb://mongo-cluster:27017/
  database: crawler_prod

worker:
  max_concurrent_tasks: 100
  heartbeat_interval: 30
  timeout: 300

scheduler:
  check_interval: 10
  max_workers: 50

monitoring:
  host: 0.0.0.0
  port: 8080
  metrics_interval: 5
```

## 许可证

MIT License