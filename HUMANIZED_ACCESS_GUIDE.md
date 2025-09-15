# 人性化访问控制指南

## 🎯 功能概述

分布式爬虫系统现已集成**人性化访问控制**，通过智能延迟和速率限制，确保对目标网站的友好访问，避免过度占用服务器资源。

## 🔧 核心特性

### 1. 智能延迟计算
- **基础延迟**: 1-3秒可配置
- **动态调整**: 根据域名访问历史自动调整延迟
- **随机因子**: 添加±50%随机性，模拟人类行为

### 2. 域名感知
- **独立控制**: 不同域名使用独立的延迟策略
- **访问统计**: 跟踪每个域名的访问频率
- **智能恢复**: 长时间未访问的域名重置延迟

### 3. 速率限制保护
- **并发控制**: 防止对单一域名过度并发请求
- **频率监控**: 实时监控访问频率
- **自动调节**: 高频访问时自动增加延迟

## 📋 使用方法

### 在爬虫中使用

```python
from distributed.worker_node import StealthCrawler

# StealthCrawler 已自动集成人性化访问控制
class MyCrawler(StealthCrawler):
    async def crawl(self, task):
        url = task.get("url")
        
        # 系统会自动在请求前添加人性化延迟
        result = await self.process_url(url)
        return result
```

### 自定义配置

```python
from distributed.access_controller import AccessController, AccessConfig

# 创建自定义配置
config = AccessConfig(
    base_delay=2.0,      # 基础延迟2秒
    min_delay=1.0,       # 最小延迟1秒
    max_delay=5.0,       # 最大延迟5秒
    rate_limit=10        # 每分钟最多10次请求
)

controller = AccessController(config)
```

## ⚙️ 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `base_delay` | 1.5秒 | 基础延迟时间 |
| `min_delay` | 1.0秒 | 最小延迟时间 |
| `max_delay` | 3.0秒 | 最大延迟时间 |
| `rate_limit` | 20 | 每分钟最大请求数 |

## 🧪 测试验证

运行测试脚本验证功能：

```bash
# 测试人性化访问控制
python test_simple_access.py

# 验证整个系统
python distributed/validate_system.py
```

## 📊 效果展示

### 测试输出示例
```
🎯 人性化访问控制测试开始
==================================================

🧪 测试域名提取:
  https://example.com/page1 -> example.com
  https://google.com/search -> google.com

🧪 测试延迟计算:
  example.com -> 延迟: 1.63秒
  google.com -> 延迟: 0.60秒

🧪 测试爬虫集成:
任务 1: https://example.com/api1
2025-09-15 10:49:29 - 等待 1.96 秒后访问 example.com
  ✅ 完成! 耗时: 1.97秒

总耗时: 5.13秒
```

## 🛡️ 保护机制

### 防止恶意占用
- **渐进式延迟**: 连续访问同一域名时延迟递增
- **冷却机制**: 高频访问后自动进入冷却期
- **异常检测**: 检测到异常访问模式时发出警告

### 合规性保证
- **robots.txt**: 自动检测和遵守爬虫协议
- **User-Agent**: 使用友好的User-Agent标识
- **错误处理**: 遇到限制时优雅降级

## 🚀 快速开始

1. **启动系统**:
   ```bash
   python start_distributed_system.py
   ```

2. **提交任务**:
   ```bash
   python test_distributed_system.py
   ```

3. **监控状态**:
   - 访问 http://localhost:8080 查看监控面板
   - 观察延迟统计和访问频率

## 🔍 故障排除

### 延迟过长
- 检查配置文件中的延迟参数
- 确认是否触发了频率限制
- 查看域名统计信息

### 访问被拒绝
- 检查目标网站的robots.txt
- 确认User-Agent设置
- 验证网络连接状态

## 📚 最佳实践

1. **合理设置延迟**: 根据目标网站的负载能力调整
2. **分布式部署**: 多个节点分散访问压力
3. **监控告警**: 设置访问频率告警阈值
4. **定期维护**: 清理访问统计缓存

---

**总结**: 人性化访问控制让爬虫更加友好和可持续，在获取数据的同时保护目标网站的正常运行。