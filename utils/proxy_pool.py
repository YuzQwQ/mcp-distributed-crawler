"""代理池管理系统

提供代理获取、验证、轮换等功能，支持多种代理源和智能负载均衡。
支持与Tor代理结合使用，提供更强的反爬虫能力。
"""

import asyncio
import aiohttp
import httpx
import json
import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ProxyType(Enum):
    """代理类型枚举"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class ProxyStatus(Enum):
    """代理状态枚举"""
    UNKNOWN = "unknown"
    ACTIVE = "active"
    FAILED = "failed"
    BANNED = "banned"
    SLOW = "slow"

@dataclass
class ProxyInfo:
    """代理信息数据类"""
    host: str
    port: int
    proxy_type: ProxyType
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    anonymity: Optional[str] = None
    source: Optional[str] = None
    
    # 性能指标
    response_time: float = 0.0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    status: ProxyStatus = ProxyStatus.UNKNOWN
    
    # 统计信息
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    def __post_init__(self):
        if isinstance(self.proxy_type, str):
            self.proxy_type = ProxyType(self.proxy_type)
        if isinstance(self.status, str):
            self.status = ProxyStatus(self.status)
    
    @property
    def url(self) -> str:
        """获取代理URL"""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type.value}://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """检查代理是否健康"""
        return (
            self.status == ProxyStatus.ACTIVE and
            self.success_rate >= 0.7 and
            self.response_time < 10.0
        )
    
    def update_stats(self, success: bool, response_time: float = 0.0):
        """更新统计信息"""
        self.total_requests += 1
        self.last_used = datetime.now()
        
        if success:
            self.successful_requests += 1
            self.response_time = (self.response_time + response_time) / 2 if self.response_time > 0 else response_time
            self.status = ProxyStatus.ACTIVE
        else:
            self.failed_requests += 1
            if self.failed_requests >= 3:
                self.status = ProxyStatus.FAILED
        
        # 更新成功率
        self.success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0

class ProxyProvider:
    """代理提供者基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def fetch_proxies(self, limit: int = 100) -> List[ProxyInfo]:
        """获取代理列表"""
        raise NotImplementedError

class FreeProxyProvider(ProxyProvider):
    """免费代理提供者"""
    
    def __init__(self):
        super().__init__("FreeProxy")
        self.api_urls = [
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        ]
    
    async def fetch_proxies(self, limit: int = 100) -> List[ProxyInfo]:
        """从免费API获取代理"""
        proxies = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for url in self.api_urls:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            text = await response.text()
                            proxies.extend(self._parse_proxy_list(text))
                except Exception as e:
                    self.logger.warning(f"获取代理失败 {url}: {e}")
        
        self.logger.info(f"从免费源获取到 {len(proxies)} 个代理")
        return proxies[:limit]
    
    def _parse_proxy_list(self, text: str) -> List[ProxyInfo]:
        """解析代理列表文本"""
        proxies = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                try:
                    host, port = line.split(':', 1)
                    proxies.append(ProxyInfo(
                        host=host.strip(),
                        port=int(port.strip()),
                        proxy_type=ProxyType.HTTP,
                        source=self.name
                    ))
                except ValueError:
                    continue
        
        return proxies

class PaidProxyProvider(ProxyProvider):
    """付费代理提供者"""
    
    def __init__(self, api_key: str, api_url: str):
        super().__init__("PaidProxy")
        self.api_key = api_key
        self.api_url = api_url
    
    async def fetch_proxies(self, limit: int = 100) -> List[ProxyInfo]:
        """从付费API获取代理"""
        # 这里需要根据具体的付费代理服务API实现
        # 示例实现
        proxies = []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(self.api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        proxies = self._parse_paid_proxy_response(data)
        except Exception as e:
            self.logger.error(f"获取付费代理失败: {e}")
        
        self.logger.info(f"从付费源获取到 {len(proxies)} 个代理")
        return proxies[:limit]
    
    def _parse_paid_proxy_response(self, data: Dict) -> List[ProxyInfo]:
        """解析付费代理API响应"""
        # 根据具体API格式实现
        return []

class ProxyValidator:
    """代理验证器"""
    
    def __init__(self, test_urls: List[str] = None, timeout: float = 10.0):
        self.test_urls = test_urls or [
            "http://httpbin.org/ip",
            "https://httpbin.org/ip",
            "http://icanhazip.com",
        ]
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.validator")
    
    async def validate_proxy(self, proxy: ProxyInfo) -> bool:
        """验证单个代理"""
        start_time = time.time()
        
        try:
            # 使用httpx进行异步请求测试
            proxy_config = {
                "http://": proxy.url,
                "https://": proxy.url,
            }
            
            async with httpx.AsyncClient(
                proxies=proxy_config,
                timeout=self.timeout,
                verify=False
            ) as client:
                # 测试多个URL
                success_count = 0
                for test_url in self.test_urls:
                    try:
                        response = await client.get(test_url)
                        if response.status_code == 200:
                            success_count += 1
                    except Exception:
                        continue
                
                response_time = time.time() - start_time
                success = success_count >= len(self.test_urls) // 2
                
                proxy.update_stats(success, response_time)
                proxy.last_checked = datetime.now()
                
                return success
                
        except Exception as e:
            self.logger.debug(f"代理验证失败 {proxy.host}:{proxy.port} - {e}")
            proxy.update_stats(False)
            proxy.last_checked = datetime.now()
            return False
    
    async def validate_proxies(self, proxies: List[ProxyInfo], max_concurrent: int = 50) -> List[ProxyInfo]:
        """批量验证代理"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(proxy):
            async with semaphore:
                return await self.validate_proxy(proxy)
        
        # 并发验证
        tasks = [validate_with_semaphore(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤有效代理
        valid_proxies = []
        for proxy, result in zip(proxies, results):
            if isinstance(result, bool) and result:
                valid_proxies.append(proxy)
        
        self.logger.info(f"验证完成: {len(valid_proxies)}/{len(proxies)} 个代理可用")
        return valid_proxies

class ProxyRotator:
    """代理轮换器"""
    
    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.current_index = 0
        self.logger = logging.getLogger(f"{__name__}.rotator")
    
    def select_proxy(self, proxies: List[ProxyInfo]) -> Optional[ProxyInfo]:
        """选择代理"""
        if not proxies:
            return None
        
        # 过滤健康的代理
        healthy_proxies = [p for p in proxies if p.is_healthy]
        if not healthy_proxies:
            # 如果没有健康的代理，使用状态未知的代理
            healthy_proxies = [p for p in proxies if p.status == ProxyStatus.UNKNOWN]
            if not healthy_proxies:
                return None
        
        if self.strategy == "round_robin":
            return self._round_robin_select(healthy_proxies)
        elif self.strategy == "random":
            return random.choice(healthy_proxies)
        elif self.strategy == "best_performance":
            return self._best_performance_select(healthy_proxies)
        else:
            return healthy_proxies[0]
    
    def _round_robin_select(self, proxies: List[ProxyInfo]) -> ProxyInfo:
        """轮询选择"""
        proxy = proxies[self.current_index % len(proxies)]
        self.current_index += 1
        return proxy
    
    def _best_performance_select(self, proxies: List[ProxyInfo]) -> ProxyInfo:
        """选择性能最佳的代理"""
        return max(proxies, key=lambda p: (p.success_rate, -p.response_time))

class ProxyPool:
    """代理池管理器"""
    
    def __init__(self, config_file: str = "proxy_pool_config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # 组件初始化
        self.providers: List[ProxyProvider] = []
        self.validator = ProxyValidator(
            timeout=self.config.get("validation_timeout", 10.0)
        )
        self.rotator = ProxyRotator(
            strategy=self.config.get("rotation_strategy", "round_robin")
        )
        
        # 代理存储
        self.proxies: List[ProxyInfo] = []
        self.last_refresh = None
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 日志
        self.logger = logging.getLogger(f"{__name__}.pool")
        
        # 初始化提供者
        self._init_providers()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        default_config = {
            "refresh_interval": 3600,  # 1小时
            "validation_timeout": 10.0,
            "rotation_strategy": "round_robin",
            "max_proxies": 1000,
            "min_success_rate": 0.7,
            "enable_free_providers": True,
            "enable_paid_providers": False,
            "paid_proxy_api_key": "",
            "paid_proxy_api_url": ""
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                self.logger.warning(f"加载配置文件失败: {e}")
        
        return default_config
    
    def _init_providers(self):
        """初始化代理提供者"""
        if self.config.get("enable_free_providers", True):
            self.providers.append(FreeProxyProvider())
        
        if self.config.get("enable_paid_providers", False):
            api_key = self.config.get("paid_proxy_api_key")
            api_url = self.config.get("paid_proxy_api_url")
            if api_key and api_url:
                self.providers.append(PaidProxyProvider(api_key, api_url))
    
    async def refresh_proxies(self, force: bool = False) -> int:
        """刷新代理池"""
        if not force and self.last_refresh:
            time_since_refresh = (datetime.now() - self.last_refresh).total_seconds()
            if time_since_refresh < self.config.get("refresh_interval", 3600):
                return len(self.proxies)
        
        self.logger.info("开始刷新代理池...")
        
        # 从所有提供者获取代理
        all_proxies = []
        for provider in self.providers:
            try:
                proxies = await provider.fetch_proxies()
                all_proxies.extend(proxies)
            except Exception as e:
                self.logger.error(f"从 {provider.name} 获取代理失败: {e}")
        
        # 去重
        unique_proxies = self._deduplicate_proxies(all_proxies)
        
        # 验证代理
        valid_proxies = await self.validator.validate_proxies(unique_proxies)
        
        # 更新代理池
        with self.lock:
            self.proxies = valid_proxies[:self.config.get("max_proxies", 1000)]
            self.last_refresh = datetime.now()
        
        self.logger.info(f"代理池刷新完成: {len(self.proxies)} 个可用代理")
        return len(self.proxies)
    
    def _deduplicate_proxies(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        """去重代理"""
        seen = set()
        unique_proxies = []
        
        for proxy in proxies:
            key = f"{proxy.host}:{proxy.port}"
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)
        
        return unique_proxies
    
    def get_proxy(self) -> Optional[ProxyInfo]:
        """获取一个代理"""
        with self.lock:
            return self.rotator.select_proxy(self.proxies)
    
    def get_proxy_config(self) -> Optional[Dict[str, str]]:
        """获取代理配置（用于httpx）"""
        proxy = self.get_proxy()
        if proxy:
            return {
                "http://": proxy.url,
                "https://": proxy.url,
            }
        return None
    
    def mark_proxy_failed(self, proxy: ProxyInfo):
        """标记代理失败"""
        proxy.update_stats(False)
        if proxy.failed_requests >= 5:
            proxy.status = ProxyStatus.BANNED
    
    def mark_proxy_success(self, proxy: ProxyInfo, response_time: float = 0.0):
        """标记代理成功"""
        proxy.update_stats(True, response_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取代理池统计信息"""
        with self.lock:
            total = len(self.proxies)
            active = len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE])
            failed = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
            
            return {
                "total_proxies": total,
                "active_proxies": active,
                "failed_proxies": failed,
                "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
                "providers": [p.name for p in self.providers]
            }
    
    async def cleanup_failed_proxies(self):
        """清理失败的代理"""
        with self.lock:
            before_count = len(self.proxies)
            self.proxies = [p for p in self.proxies if p.status != ProxyStatus.FAILED]
            after_count = len(self.proxies)
            
            if before_count != after_count:
                self.logger.info(f"清理了 {before_count - after_count} 个失败的代理")

# 全局代理池实例
_proxy_pool = None

def get_proxy_pool() -> ProxyPool:
    """获取全局代理池实例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool

async def init_proxy_pool() -> ProxyPool:
    """初始化代理池"""
    pool = get_proxy_pool()
    await pool.refresh_proxies()
    return pool