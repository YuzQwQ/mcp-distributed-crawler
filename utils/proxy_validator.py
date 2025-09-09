"""代理验证器实现

提供全面的代理验证功能，包括连接性测试、速度测试、匿名性检测等。
支持批量验证和智能重试机制。
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from urllib.parse import urlparse
import socket
from .proxy_pool import ProxyInfo, ProxyStatus, ProxyValidator

logger = logging.getLogger(__name__)

class EnhancedProxyValidator(ProxyValidator):
    """增强的代理验证器"""
    
    def __init__(self, config: Dict = None):
        super().__init__()
        self.config = config or {}
        
        # 验证配置
        self.timeout = self.config.get("timeout", 10)
        self.max_retries = self.config.get("max_retries", 2)
        self.concurrent_limit = self.config.get("concurrent_limit", 50)
        self.speed_test_url = self.config.get("speed_test_url", "http://httpbin.org/ip")
        self.anonymity_test_url = self.config.get("anonymity_test_url", "http://httpbin.org/headers")
        
        # 测试目标网站
        self.test_urls = self.config.get("test_urls", [
            "http://httpbin.org/ip",
            "https://httpbin.org/ip",
            "http://www.google.com",
            "https://www.baidu.com"
        ])
        
        # IP检测服务
        self.ip_check_services = [
            "http://httpbin.org/ip",
            "http://icanhazip.com",
            "http://ipinfo.io/ip",
            "http://api.ipify.org"
        ]
        
        # 验证统计
        self.validation_stats = {
            "total_tested": 0,
            "passed": 0,
            "failed": 0,
            "start_time": None
        }
    
    async def validate_proxy(self, proxy: ProxyInfo) -> bool:
        """验证单个代理"""
        self.validation_stats["total_tested"] += 1
        
        if self.validation_stats["start_time"] is None:
            self.validation_stats["start_time"] = time.time()
        
        try:
            # 基础连接测试
            if not await self._test_basic_connectivity(proxy):
                proxy.status = ProxyStatus.FAILED
                proxy.last_checked = datetime.now()
                self.validation_stats["failed"] += 1
                return False
            
            # 速度测试
            speed = await self._test_speed(proxy)
            if speed is None:
                proxy.status = ProxyStatus.FAILED
                proxy.last_checked = datetime.now()
                self.validation_stats["failed"] += 1
                return False
            
            proxy.response_time = speed
            
            # 匿名性测试
            anonymity = await self._test_anonymity(proxy)
            if anonymity:
                proxy.anonymity = anonymity
            
            # 地理位置检测
            location = await self._detect_location(proxy)
            if location:
                proxy.country = location.get("country")
                proxy.city = location.get("city")
            
            # 标记为可用
            proxy.status = ProxyStatus.ACTIVE
            proxy.last_checked = datetime.now()
            proxy.success_count = getattr(proxy, 'success_count', 0) + 1
            
            self.validation_stats["passed"] += 1
            self.logger.debug(f"代理验证成功: {proxy.host}:{proxy.port} (速度: {speed:.2f}s)")
            return True
            
        except Exception as e:
            proxy.status = ProxyStatus.FAILED
            proxy.last_checked = datetime.now()
            proxy.failure_count = getattr(proxy, 'failure_count', 0) + 1
            self.validation_stats["failed"] += 1
            self.logger.debug(f"代理验证失败: {proxy.host}:{proxy.port} - {e}")
            return False
    
    async def validate_proxies(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        """批量验证代理"""
        self.logger.info(f"开始验证 {len(proxies)} 个代理...")
        
        # 重置统计
        self.validation_stats = {
            "total_tested": 0,
            "passed": 0,
            "failed": 0,
            "start_time": time.time()
        }
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(self.concurrent_limit)
        
        async def validate_with_semaphore(proxy):
            async with semaphore:
                return await self.validate_proxy(proxy)
        
        # 并发验证
        tasks = [validate_with_semaphore(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤有效代理
        valid_proxies = []
        for i, (proxy, result) in enumerate(zip(proxies, results)):
            if isinstance(result, Exception):
                self.logger.warning(f"代理验证异常: {proxy.host}:{proxy.port} - {result}")
                proxy.status = ProxyStatus.FAILED
            elif result:
                valid_proxies.append(proxy)
        
        # 输出统计信息
        elapsed = time.time() - self.validation_stats["start_time"]
        self.logger.info(
            f"代理验证完成: {self.validation_stats['passed']}/{self.validation_stats['total_tested']} "
            f"通过验证 (耗时: {elapsed:.1f}s)"
        )
        
        return valid_proxies
    
    async def validate_batch(self, proxies: List[ProxyInfo], max_concurrent: int = None) -> List[bool]:
        """批量验证代理（返回布尔结果列表）"""
        if max_concurrent:
            original_limit = self.concurrent_limit
            self.concurrent_limit = max_concurrent
        
        try:
            # 创建信号量限制并发数
            semaphore = asyncio.Semaphore(self.concurrent_limit)
            
            async def validate_with_semaphore(proxy):
                async with semaphore:
                    return await self.validate_proxy(proxy)
            
            # 并发验证
            tasks = [validate_with_semaphore(proxy) for proxy in proxies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 转换为布尔结果
            bool_results = []
            for result in results:
                if isinstance(result, Exception):
                    bool_results.append(False)
                else:
                    bool_results.append(bool(result))
            
            return bool_results
            
        finally:
            if max_concurrent:
                self.concurrent_limit = original_limit
    
    async def _test_basic_connectivity(self, proxy: ProxyInfo) -> bool:
        """基础连接性测试"""
        for attempt in range(self.max_retries + 1):
            try:
                connector = self._create_proxy_connector(proxy)
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                ) as session:
                    
                    # 测试HTTP连接
                    async with session.get("http://httpbin.org/ip") as response:
                        if response.status == 200:
                            return True
                
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(1)  # 重试前等待
                    continue
                self.logger.debug(f"连接测试失败: {proxy.host}:{proxy.port} - {e}")
        
        return False
    
    async def _test_speed(self, proxy: ProxyInfo) -> Optional[float]:
        """速度测试"""
        try:
            connector = self._create_proxy_connector(proxy)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            ) as session:
                
                start_time = time.time()
                async with session.get(self.speed_test_url) as response:
                    if response.status == 200:
                        await response.read()  # 确保完全下载
                        return time.time() - start_time
                
        except Exception as e:
            self.logger.debug(f"速度测试失败: {proxy.host}:{proxy.port} - {e}")
        
        return None
    
    async def _test_anonymity(self, proxy: ProxyInfo) -> Optional[str]:
        """匿名性测试"""
        try:
            connector = self._create_proxy_connector(proxy)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            ) as session:
                
                async with session.get(self.anonymity_test_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        headers = data.get("headers", {})
                        
                        # 检查是否暴露真实IP
                        forwarded_headers = [
                            "X-Forwarded-For", "X-Real-IP", "X-Originating-IP",
                            "Client-IP", "Via", "Proxy-Connection"
                        ]
                        
                        has_proxy_headers = any(header in headers for header in forwarded_headers)
                        
                        if not has_proxy_headers:
                            return "elite"  # 高匿名
                        elif "Via" in headers or "Proxy-Connection" in headers:
                            return "transparent"  # 透明代理
                        else:
                            return "anonymous"  # 匿名代理
                
        except Exception as e:
            self.logger.debug(f"匿名性测试失败: {proxy.host}:{proxy.port} - {e}")
        
        return None
    
    async def _detect_location(self, proxy: ProxyInfo) -> Optional[Dict]:
        """检测代理地理位置"""
        try:
            connector = self._create_proxy_connector(proxy)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            ) as session:
                
                # 尝试多个IP信息服务
                location_services = [
                    "http://ipinfo.io/json",
                    "http://ip-api.com/json",
                    "http://freegeoip.app/json/"
                ]
                
                for service_url in location_services:
                    try:
                        async with session.get(service_url) as response:
                            if response.status == 200:
                                data = await response.json()
                                return {
                                    "country": data.get("country") or data.get("countryCode"),
                                    "city": data.get("city"),
                                    "region": data.get("region") or data.get("regionName"),
                                    "ip": data.get("ip") or data.get("query")
                                }
                    except Exception:
                        continue
                
        except Exception as e:
            self.logger.debug(f"位置检测失败: {proxy.host}:{proxy.port} - {e}")
        
        return None
    
    def _create_proxy_connector(self, proxy: ProxyInfo) -> aiohttp.BaseConnector:
        """创建代理连接器"""
        from aiohttp_socks import ProxyConnector, ProxyType as SocksProxyType
        
        if proxy.proxy_type.value in ["socks4", "socks5"]:
            # SOCKS代理
            socks_type = SocksProxyType.SOCKS5 if proxy.proxy_type.value == "socks5" else SocksProxyType.SOCKS4
            
            return ProxyConnector(
                proxy_type=socks_type,
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                rdns=True
            )
        else:
            # HTTP/HTTPS代理
            proxy_url = f"http://{proxy.host}:{proxy.port}"
            if proxy.username and proxy.password:
                proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            
            return aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
    
    async def health_check(self, proxy: ProxyInfo) -> bool:
        """健康检查（快速验证）"""
        try:
            connector = self._create_proxy_connector(proxy)
            timeout = aiohttp.ClientTimeout(total=5)  # 更短的超时时间
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "HealthCheck/1.0"}
            ) as session:
                
                async with session.get("http://httpbin.org/status/200") as response:
                    return response.status == 200
                
        except Exception:
            return False
    
    def get_validation_stats(self) -> Dict:
        """获取验证统计信息"""
        stats = self.validation_stats.copy()
        if stats["start_time"]:
            stats["elapsed_time"] = time.time() - stats["start_time"]
            if stats["total_tested"] > 0:
                stats["success_rate"] = stats["passed"] / stats["total_tested"]
                stats["avg_time_per_proxy"] = stats["elapsed_time"] / stats["total_tested"]
        return stats

class SmartProxyValidator(EnhancedProxyValidator):
    """智能代理验证器（带学习功能）"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.failure_patterns = {}  # 失败模式记录
        self.success_patterns = {}  # 成功模式记录
        self.adaptive_timeout = True
        
    async def validate_proxy(self, proxy: ProxyInfo) -> bool:
        """智能验证（带自适应超时）"""
        # 根据历史数据调整超时时间
        if self.adaptive_timeout:
            self.timeout = self._calculate_adaptive_timeout(proxy)
        
        result = await super().validate_proxy(proxy)
        
        # 记录验证模式
        self._record_validation_pattern(proxy, result)
        
        return result
    
    def _calculate_adaptive_timeout(self, proxy: ProxyInfo) -> float:
        """计算自适应超时时间"""
        base_timeout = self.config.get("timeout", 10)
        
        # 根据代理类型调整
        if proxy.proxy_type.value in ["socks4", "socks5"]:
            base_timeout *= 1.2  # SOCKS代理通常较慢
        
        # 根据历史响应时间调整
        if hasattr(proxy, 'response_time') and proxy.response_time:
            # 使用历史响应时间的1.5倍作为超时时间
            adaptive_timeout = proxy.response_time * 1.5
            return max(min(adaptive_timeout, base_timeout * 2), base_timeout * 0.5)
        
        return base_timeout
    
    def _record_validation_pattern(self, proxy: ProxyInfo, success: bool):
        """记录验证模式"""
        pattern_key = f"{proxy.proxy_type.value}:{proxy.country or 'unknown'}"
        
        if success:
            if pattern_key not in self.success_patterns:
                self.success_patterns[pattern_key] = []
            self.success_patterns[pattern_key].append({
                "timestamp": datetime.now(),
                "response_time": getattr(proxy, 'response_time', None)
            })
        else:
            if pattern_key not in self.failure_patterns:
                self.failure_patterns[pattern_key] = []
            self.failure_patterns[pattern_key].append({
                "timestamp": datetime.now(),
                "reason": getattr(proxy, 'last_error', 'unknown')
            })
    
    def get_pattern_analysis(self) -> Dict:
        """获取模式分析结果"""
        analysis = {
            "success_patterns": {},
            "failure_patterns": {},
            "recommendations": []
        }
        
        # 分析成功模式
        for pattern, records in self.success_patterns.items():
            if len(records) >= 5:  # 至少5个样本
                avg_response_time = sum(
                    r["response_time"] for r in records if r["response_time"]
                ) / len([r for r in records if r["response_time"]])
                
                analysis["success_patterns"][pattern] = {
                    "count": len(records),
                    "avg_response_time": avg_response_time,
                    "reliability": "high" if len(records) > 10 else "medium"
                }
        
        # 分析失败模式
        for pattern, records in self.failure_patterns.items():
            if len(records) >= 3:
                analysis["failure_patterns"][pattern] = {
                    "count": len(records),
                    "common_reasons": self._get_common_failure_reasons(records)
                }
        
        # 生成建议
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _get_common_failure_reasons(self, records: List[Dict]) -> List[str]:
        """获取常见失败原因"""
        reasons = [r["reason"] for r in records]
        reason_counts = {}
        
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return sorted(reason_counts.keys(), key=lambda x: reason_counts[x], reverse=True)[:3]
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于成功模式的建议
        best_patterns = sorted(
            analysis["success_patterns"].items(),
            key=lambda x: (x[1]["count"], -x[1]["avg_response_time"]),
            reverse=True
        )[:3]
        
        if best_patterns:
            recommendations.append(
                f"推荐优先使用: {', '.join([p[0] for p in best_patterns])}"
            )
        
        # 基于失败模式的建议
        worst_patterns = sorted(
            analysis["failure_patterns"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:2]
        
        if worst_patterns:
            recommendations.append(
                f"建议避免使用: {', '.join([p[0] for p in worst_patterns])}"
            )
        
        return recommendations

# 工厂函数
def create_proxy_validator(validator_type: str = "enhanced", **kwargs) -> ProxyValidator:
    """创建代理验证器"""
    if validator_type == "enhanced":
        return EnhancedProxyValidator(kwargs.get("config", {}))
    elif validator_type == "smart":
        return SmartProxyValidator(kwargs.get("config", {}))
    else:
        raise ValueError(f"不支持的验证器类型: {validator_type}")