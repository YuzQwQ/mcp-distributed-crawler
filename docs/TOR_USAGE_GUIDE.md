# Tor Proxy Usage Guide

本指南介绍如何在MCP客户端中配置和使用Tor代理功能，用于增强网络爬虫的匿名性和反反爬虫能力。

## 功能概述

### 基础功能
- **start_tor_proxy**: 启动Tor代理服务
- **stop_tor_proxy**: 停止Tor代理服务
- **get_tor_status**: 获取Tor代理运行状态
- **change_tor_identity**: 手动更换Tor身份（获取新IP）

### 高级功能
- **check_tor_ip**: 检查当前通过Tor的IP地址
- **test_tor_connection**: 测试Tor代理连接质量
- **validate_tor_config**: 验证Tor配置是否正确
- **auto_rotate_tor_identity**: 自动轮换Tor身份
- **get_tor_circuit_info**: 获取Tor电路信息

## 配置步骤

### 1. 安装Tor Browser

下载并安装Tor Browser：https://www.torproject.org/download/

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```env
# 启用Tor代理
USE_TOR=true

# Tor可执行文件路径（根据实际安装路径修改）
TOR_EXECUTABLE_PATH=D:\Tor Browser\Browser\TorBrowser\Tor\tor.exe

# 代理端口配置
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# 控制端口密码（可选，建议设置）
TOR_PASSWORD=your_password_here
```

### 3. 安装依赖

确保安装了httpx-socks库：

```bash
pip install httpx-socks
```

## 使用示例

### 基础使用流程

1. **验证配置**
   ```
   调用: validate_tor_config
   ```

2. **启动Tor代理**
   ```
   调用: start_tor_proxy
   ```

3. **检查状态和IP**
   ```
   调用: get_tor_status
   调用: check_tor_ip
   ```

4. **测试连接**
   ```
   调用: test_tor_connection
   ```

### 高级使用场景

#### 场景1：长时间爬虫任务

对于需要长时间运行的爬虫任务，建议定期更换IP：

```
# 每5分钟自动更换一次IP，最多更换20次
调用: auto_rotate_tor_identity
参数: interval_seconds=300, max_rotations=20
```

#### 场景2：高频爬虫任务

对于高频率的爬虫请求，可以手动控制IP更换时机：

```
# 在检测到反爬虫机制时手动更换IP
调用: change_tor_identity

# 验证IP是否已更换
调用: check_tor_ip
```

#### 场景3：调试和监控

```
# 获取详细的电路信息
调用: get_tor_circuit_info

# 测试多个端点的连接质量
调用: test_tor_connection
```

## 最佳实践

### 1. 安全建议
- 设置控制端口密码（TOR_PASSWORD）
- 定期更换密码
- 不要在日志中记录敏感信息

### 2. 性能优化
- 合理设置身份更换间隔（建议不少于60秒）
- 避免过于频繁的IP更换，以免影响Tor网络
- 在爬虫任务开始前预先测试连接

### 3. 错误处理
- 在网络请求中添加适当的超时设置
- 实现重试机制处理连接失败
- 监控Tor进程状态，必要时重启

### 4. 合规使用
- 遵守目标网站的robots.txt
- 控制请求频率，避免对服务器造成压力
- 尊重网站的使用条款

## 故障排除

### 常见问题

1. **Tor启动失败**
   - 检查TOR_EXECUTABLE_PATH是否正确
   - 确认Tor Browser已正确安装
   - 检查端口是否被占用

2. **连接超时**
   - 增加超时时间设置
   - 检查网络连接
   - 尝试更换Tor身份

3. **IP未更换**
   - 等待更长时间让新电路建立
   - 检查控制端口连接
   - 重启Tor服务

4. **配置验证失败**
   - 使用validate_tor_config检查具体问题
   - 确认所有必需的依赖已安装
   - 检查.env文件配置

### 调试步骤

1. 运行配置验证：`validate_tor_config`
2. 检查Tor状态：`get_tor_status`
3. 测试连接：`test_tor_connection`
4. 查看电路信息：`get_tor_circuit_info`

## 注意事项

- Tor代理会增加网络延迟，请合理设置超时时间
- 频繁更换IP可能触发某些网站的安全机制
- 在生产环境中使用前，请充分测试所有功能
- 定期更新Tor Browser以获得最新的安全特性

## 技术支持

如果遇到问题，请：
1. 首先运行`validate_tor_config`检查配置
2. 查看Tor日志文件（./tor_data/tor.log）
3. 确认网络连接正常
4. 检查防火墙设置

---

*本指南基于Tor Browser和MCP客户端的当前版本编写，具体配置可能因版本而异。*