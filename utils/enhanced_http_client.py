"""增强的HTTP客户端管理器

集成代理池、Tor代理和智能重试机制的HTTP客户端。
支持自动故障转移和负载均衡。
"""

import asyncio
import httpx
import aiohttp
import requests
import logging
import time
import random
from typing import Dict, List, Optional, Union, Any, Callable
from datetime import datetime, timedelta
from urllib.parse import urlparse
from contextlib import asynccontextmanager

# 导入代理池组件
from .proxy_pool import ProxyPool, ProxyInfo, ProxyStatus
from .proxy_providers import create_proxy_provider
from .proxy_validator import create_proxy_validator
from .proxy_rotator import create_proxy_rotator

logger = logging.getLogger(__name__)

class EnhancedHttpClient:
    """增强的HTTP客户端"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 基础配置
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        
        # 代理池配置
        self.use_proxy_pool = self.config.get("use_proxy_pool", False)
        self.use_tor = self.config.get("use_tor", False)
        self.proxy_pool_manager = None
        
        # Tor配置
        self.tor_socks_port = self.config.get("tor_socks_port", 9050)
        self.tor_proxy_url = f"socks5://127.0.0.1:{self.tor_socks_port}"
        
        # 请求头配置
        self.default_headers = self.config.get("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxy_requests": 0,
            "tor_requests": 0,
            "direct_requests": 0,
            "retry_count": 0
        }
        
        # 初始化代理池
        if self.use_proxy_pool:
            self._init_proxy_pool()
    
    def _init_proxy_pool(self):
        """初始化代理池"""
        try:
            # 创建代理提供者
            providers = []
            
            # 免费代理提供者
            if self.config.get("use_free_proxies", True):
                free_provider = create_proxy_provider("free")
                providers.append(free_provider)
            
            # 付费代理提供者
            premium_configs = self.config.get("premium_proxies", [])
            for premium_config in premium_configs:
                premium_provider = create_proxy_provider(
                    "premium",
                    service_name=premium_config["service_name"],
                    api_key=premium_config["api_key"],
                    api_url=premium_config["api_url"],
                    config=premium_config.get("config", {})
                )
                providers.append(premium_provider)
            
            # 本地代理文件
            local_proxy_file = self.config.get("local_proxy_file")
            if local_proxy_file:
                local_provider = create_proxy_provider("local", proxy_file=local_proxy_file)
                providers.append(local_provider)
            
            # 创建验证器
            validator_config = self.config.get("validator_config", {})
            validator = create_proxy_validator("enhanced", config=validator_config)
            
            # 创建轮换器
            rotation_strategy = self.config.get("rotation_strategy", "adaptive")
            rotator = create_proxy_rotator(rotation_strategy)
            
            # 创建代理池管理器
            pool_config = self.config.get("pool_config", {})
            self.proxy_pool_manager = ProxyPool(
                providers=providers,
                validator=validator,
                rotator=rotator,
                config=pool_config
            )
            
            logger.info("代理池初始化成功")
            
        except Exception as e:
            logger.error(f"代理池初始化失败: {e}")
            self.use_proxy_pool = False
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """异步GET请求"""
        return await self._request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """异步POST请求"""
        return await self._request("POST", url, **kwargs)
    
    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """执行HTTP请求（带重试和代理轮换）"""
        self.stats["total_requests"] += 1
        
        # 合并请求头
        headers = self.default_headers.copy()
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers
        
        # 设置超时
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 选择连接方式
                client_config = await self._get_client_config(url, attempt)
                
                async with httpx.AsyncClient(**client_config) as client:
                    response = await client.request(method, url, **kwargs)
                    
                    # 检查响应状态
                    if response.status_code < 400:
                        self.stats["successful_requests"] += 1
                        
                        # 记录代理使用成功
                        if "proxy" in client_config:
                            await self._record_proxy_success(client_config["proxy"], response)
                        
                        return response
                    else:
                        raise httpx.HTTPStatusError(
                            f"HTTP {response.status_code}",
                            request=response.request,
                            response=response
                        )
                        
            except Exception as e:
                last_exception = e
                
                # 记录代理使用失败
                if "proxy" in locals() and "client_config" in locals():
                    await self._record_proxy_failure(client_config.get("proxy"), str(e))
                
                if attempt < self.max_retries:
                    self.stats["retry_count"] += 1
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"请求失败，{delay:.1f}秒后重试 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"请求最终失败: {url} - {e}")
        
        self.stats["failed_requests"] += 1
        raise last_exception
    
    async def _get_client_config(self, url: str, attempt: int) -> Dict:
        """获取HTTP客户端配置"""
        config = {
            "follow_redirects": True,
            "verify": False,  # 在某些代理环境下可能需要
        }
        
        # 根据尝试次数选择连接方式
        if attempt == 0 and self.use_proxy_pool and self.proxy_pool_manager:
            # 第一次尝试：使用代理池
            proxy = await self._get_proxy_from_pool(url)
            if proxy:
                config.update(await self._create_proxy_config(proxy))
                self.stats["proxy_requests"] += 1
                return config
        
        if attempt == 1 and self.use_tor:
            # 第二次尝试：使用Tor
            config.update(await self._create_tor_config())
            self.stats["tor_requests"] += 1
            return config
        
        # 最后尝试：直连
        self.stats["direct_requests"] += 1
        return config
    
    async def _get_proxy_from_pool(self, url: str) -> Optional[ProxyInfo]:
        """从代理池获取代理"""
        if not self.proxy_pool_manager:
            return None
        
        try:
            # 解析目标域名
            parsed_url = urlparse(url)
            target_domain = parsed_url.netloc
            
            # 获取代理
            proxy = await self.proxy_pool_manager.get_proxy(
                target_domain=target_domain,
                request_type="http"
            )
            
            return proxy
            
        except Exception as e:
            logger.warning(f"从代理池获取代理失败: {e}")
            return None
    
    async def _create_proxy_config(self, proxy: ProxyInfo) -> Dict:
        """创建代理配置"""
        config = {}
        
        try:
            if proxy.proxy_type.value in ["socks4", "socks5"]:
                # SOCKS代理
                from httpx_socks import AsyncProxyTransport
                
                proxy_url = f"{proxy.proxy_type.value}://{proxy.host}:{proxy.port}"
                if proxy.username and proxy.password:
                    proxy_url = f"{proxy.proxy_type.value}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                
                transport = AsyncProxyTransport.from_url(proxy_url)
                config["transport"] = transport
                
            else:
                # HTTP/HTTPS代理
                proxy_url = f"http://{proxy.host}:{proxy.port}"
                if proxy.username and proxy.password:
                    proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                
                config["proxies"] = {
                    "http://": proxy_url,
                    "https://": proxy_url
                }
            
            # 保存代理信息用于后续记录
            config["proxy"] = proxy
            
        except ImportError:
            logger.warning("httpx-socks未安装，无法使用SOCKS代理")
        except Exception as e:
            logger.warning(f"创建代理配置失败: {e}")
        
        return config
    
    async def _create_tor_config(self) -> Dict:
        """创建Tor配置"""
        config = {}
        
        try:
            from httpx_socks import AsyncProxyTransport
            
            transport = AsyncProxyTransport.from_url(self.tor_proxy_url)
            config["transport"] = transport
            
        except ImportError:
            logger.warning("httpx-socks未安装，无法使用Tor代理")
        except Exception as e:
            logger.warning(f"创建Tor配置失败: {e}")
        
        return config
    
    async def _record_proxy_success(self, proxy: ProxyInfo, response: httpx.Response):
        """记录代理使用成功"""
        if not self.proxy_pool_manager or not proxy:
            return
        
        try:
            response_time = getattr(response, 'elapsed', None)
            if response_time:
                response_time = response_time.total_seconds()
            
            await self.proxy_pool_manager.record_usage(
                proxy, 
                success=True, 
                response_time=response_time
            )
            
        except Exception as e:
            logger.debug(f"记录代理成功使用失败: {e}")
    
    async def _record_proxy_failure(self, proxy: ProxyInfo, error: str):
        """记录代理使用失败"""
        if not self.proxy_pool_manager or not proxy:
            return
        
        try:
            await self.proxy_pool_manager.record_usage(
                proxy, 
                success=False, 
                error=error
            )
            
        except Exception as e:
            logger.debug(f"记录代理失败使用失败: {e}")
    
    def get_sync(self, url: str, **kwargs) -> requests.Response:
        """同步GET请求（兼容性接口）"""
        return self._request_sync("GET", url, **kwargs)
    
    def post_sync(self, url: str, **kwargs) -> requests.Response:
        """同步POST请求（兼容性接口）"""
        return self._request_sync("POST", url, **kwargs)
    
    def _request_sync(self, method: str, url: str, **kwargs) -> requests.Response:
        """同步HTTP请求（用于兼容现有代码）"""
        self.stats["total_requests"] += 1
        
        # 合并请求头
        headers = self.default_headers.copy()
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers
        
        # 设置超时
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 获取代理配置
                proxies = self._get_sync_proxy_config(url, attempt)
                if proxies:
                    kwargs["proxies"] = proxies
                
                response = requests.request(method, url, **kwargs)
                
                if response.status_code < 400:
                    self.stats["successful_requests"] += 1
                    return response
                else:
                    response.raise_for_status()
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    self.stats["retry_count"] += 1
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"同步请求失败，{delay:.1f}秒后重试: {e}")
                    time.sleep(delay)
        
        self.stats["failed_requests"] += 1
        raise last_exception
    
    def _get_sync_proxy_config(self, url: str, attempt: int) -> Optional[Dict[str, str]]:
        """获取同步请求的代理配置"""
        if attempt == 0 and self.use_tor:
            # 优先使用Tor
            self.stats["tor_requests"] += 1
            return {
                "http": self.tor_proxy_url,
                "https": self.tor_proxy_url
            }
        
        # 其他情况直连
        self.stats["direct_requests"] += 1
        return None
    
    async def start_proxy_pool(self):
        """启动代理池"""
        if self.proxy_pool_manager:
            await self.proxy_pool_manager.start()
            logger.info("代理池已启动")
    
    async def stop_proxy_pool(self):
        """停止代理池"""
        if self.proxy_pool_manager:
            await self.proxy_pool_manager.stop()
            logger.info("代理池已停止")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()
        
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
            stats["failure_rate"] = stats["failed_requests"] / stats["total_requests"]
        
        if self.proxy_pool_manager:
            pool_stats = self.proxy_pool_manager.get_stats()
            stats["proxy_pool"] = pool_stats
        
        return stats
    
    async def close(self):
        """关闭HTTP客户端"""
        try:
            if self.proxy_pool_manager:
                await self.stop_proxy_pool()
            logger.info("HTTP客户端已关闭")
        except Exception as e:
            logger.error(f"关闭HTTP客户端失败: {e}")
    
    @asynccontextmanager
    async def session(self):
        """异步上下文管理器"""
        if self.use_proxy_pool:
            await self.start_proxy_pool()
        
        try:
            yield self
        finally:
            if self.use_proxy_pool:
                await self.stop_proxy_pool()

class HttpClientFactory:
    """HTTP客户端工厂"""
    
    @staticmethod
    def create_client(config: Dict = None) -> EnhancedHttpClient:
        """创建HTTP客户端"""
        return EnhancedHttpClient(config)
    
    @staticmethod
    def create_proxy_client(proxy_config: Dict = None) -> EnhancedHttpClient:
        """创建带代理池的HTTP客户端"""
        config = {
            "use_proxy_pool": True,
            "use_tor": True,
            "max_retries": 3,
            "timeout": 30
        }
        
        if proxy_config:
            config.update(proxy_config)
        
        return EnhancedHttpClient(config)
    
    @staticmethod
    def create_tor_client(tor_config: Dict = None) -> EnhancedHttpClient:
        """创建Tor客户端"""
        config = {
            "use_tor": True,
            "use_proxy_pool": False,
            "max_retries": 2,
            "timeout": 30
        }
        
        if tor_config:
            config.update(tor_config)
        
        return EnhancedHttpClient(config)
    
    @staticmethod
    def create_simple_client() -> EnhancedHttpClient:
        """创建简单客户端（无代理）"""
        config = {
            "use_proxy_pool": False,
            "use_tor": False,
            "max_retries": 2,
            "timeout": 15
        }
        
        return EnhancedHttpClient(config)

# 全局客户端实例（单例模式）
_global_client = None

def get_global_client(config: Dict = None) -> EnhancedHttpClient:
    """获取全局HTTP客户端实例"""
    global _global_client
    
    if _global_client is None:
        _global_client = HttpClientFactory.create_proxy_client(config)
    
    return _global_client

def reset_global_client():
    """重置全局客户端"""
    global _global_client
    _global_client = None

# 便捷函数
async def get(url: str, **kwargs) -> httpx.Response:
    """便捷的异步GET请求"""
    client = get_global_client()
    return await client.get(url, **kwargs)

async def post(url: str, **kwargs) -> httpx.Response:
    """便捷的异步POST请求"""
    client = get_global_client()
    return await client.post(url, **kwargs)

def get_sync(url: str, **kwargs) -> requests.Response:
    """便捷的同步GET请求"""
    client = get_global_client()
    return client.get_sync(url, **kwargs)

def post_sync(url: str, **kwargs) -> requests.Response:
    """便捷的同步POST请求"""
    client = get_global_client()
    return client.post_sync(url, **kwargs)