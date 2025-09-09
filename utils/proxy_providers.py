"""代理提供者实现

包含多种代理源的实现，支持免费和付费代理服务。
提供智能解析、去重和质量评估功能。
"""

import asyncio
import aiohttp
import json
import re
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import base64
from .proxy_pool import ProxyInfo, ProxyType, ProxyProvider

logger = logging.getLogger(__name__)

class EnhancedFreeProxyProvider(ProxyProvider):
    """增强的免费代理提供者"""
    
    def __init__(self):
        super().__init__("EnhancedFreeProxy")
        self.api_sources = {
            "proxy_list_download": {
                "urls": [
                    "https://www.proxy-list.download/api/v1/get?type=http",
                    "https://www.proxy-list.download/api/v1/get?type=https",
                    "https://www.proxy-list.download/api/v1/get?type=socks4",
                    "https://www.proxy-list.download/api/v1/get?type=socks5"
                ],
                "parser": self._parse_simple_list
            },
            "proxyscrape": {
                "urls": [
                    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                    "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all",
                    "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all"
                ],
                "parser": self._parse_simple_list
            },
            "github_lists": {
                "urls": [
                    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
                    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
                    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
                    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
                    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
                    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"
                ],
                "parser": self._parse_simple_list
            },
            "proxyrotator": {
                "urls": [
                    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
                    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt",
                    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt",
                    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt"
                ],
                "parser": self._parse_simple_list
            }
        }
        
        # 代理类型映射
        self.type_mapping = {
            "http": ProxyType.HTTP,
            "https": ProxyType.HTTPS,
            "socks4": ProxyType.SOCKS4,
            "socks5": ProxyType.SOCKS5
        }
    
    async def fetch_proxies(self, limit: int = 100) -> List[ProxyInfo]:
        """从所有免费源获取代理"""
        all_proxies = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        ) as session:
            
            for source_name, source_config in self.api_sources.items():
                self.logger.info(f"正在从 {source_name} 获取代理...")
                
                for url in source_config["urls"]:
                    try:
                        proxy_type = self._extract_proxy_type_from_url(url)
                        proxies = await self._fetch_from_url(session, url, source_config["parser"], proxy_type)
                        
                        # 标记代理源
                        for proxy in proxies:
                            proxy.source = source_name
                        
                        all_proxies.extend(proxies)
                        self.logger.debug(f"从 {url} 获取到 {len(proxies)} 个代理")
                        
                        # 避免请求过于频繁
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        self.logger.warning(f"从 {url} 获取代理失败: {e}")
        
        # 去重
        unique_proxies = self._deduplicate_proxies(all_proxies)
        self.logger.info(f"从免费源获取到 {len(unique_proxies)} 个唯一代理")
        
        return unique_proxies
    
    async def _fetch_from_url(self, session: aiohttp.ClientSession, url: str, parser, proxy_type: ProxyType) -> List[ProxyInfo]:
        """从单个URL获取代理"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    return parser(content, proxy_type)
                else:
                    self.logger.warning(f"HTTP {response.status} from {url}")
                    return []
        except Exception as e:
            self.logger.error(f"请求 {url} 失败: {e}")
            return []
    
    def _extract_proxy_type_from_url(self, url: str) -> ProxyType:
        """从URL中提取代理类型"""
        url_lower = url.lower()
        
        if "socks5" in url_lower:
            return ProxyType.SOCKS5
        elif "socks4" in url_lower:
            return ProxyType.SOCKS4
        elif "https" in url_lower:
            return ProxyType.HTTPS
        else:
            return ProxyType.HTTP
    
    def _parse_simple_list(self, content: str, proxy_type: ProxyType) -> List[ProxyInfo]:
        """解析简单的代理列表"""
        proxies = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 支持多种格式
            proxy_info = self._parse_proxy_line(line, proxy_type)
            if proxy_info:
                proxies.append(proxy_info)
        
        return proxies[:limit]
    
    def _parse_proxy_line(self, line: str, default_type: ProxyType) -> Optional[ProxyInfo]:
        """解析单行代理信息"""
        try:
            # 移除多余的空格和特殊字符
            line = re.sub(r'[\r\n\t]', '', line).strip()
            
            # 格式1: host:port
            if re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', line):
                host, port = line.split(':')
                return ProxyInfo(
                    host=host,
                    port=int(port),
                    proxy_type=default_type,
                    source=self.name
                )
            
            # 格式2: protocol://host:port
            protocol_match = re.match(r'^(https?|socks[45]?)://([^:]+):(\d+)$', line)
            if protocol_match:
                protocol, host, port = protocol_match.groups()
                proxy_type = self.type_mapping.get(protocol.lower(), default_type)
                return ProxyInfo(
                    host=host,
                    port=int(port),
                    proxy_type=proxy_type,
                    source=self.name
                )
            
            # 格式3: host:port:username:password
            auth_match = re.match(r'^([^:]+):(\d+):([^:]+):(.+)$', line)
            if auth_match:
                host, port, username, password = auth_match.groups()
                return ProxyInfo(
                    host=host,
                    port=int(port),
                    proxy_type=default_type,
                    username=username,
                    password=password,
                    source=self.name
                )
            
            # 格式4: JSON格式
            if line.startswith('{') and line.endswith('}'):
                try:
                    data = json.loads(line)
                    return self._parse_json_proxy(data, default_type)
                except json.JSONDecodeError:
                    pass
            
        except (ValueError, IndexError) as e:
            self.logger.debug(f"解析代理行失败 '{line}': {e}")
        
        return None
    
    def _parse_json_proxy(self, data: Dict, default_type: ProxyType) -> Optional[ProxyInfo]:
        """解析JSON格式的代理信息"""
        try:
            host = data.get('host') or data.get('ip') or data.get('address')
            port = data.get('port')
            
            if not host or not port:
                return None
            
            proxy_type_str = data.get('type', '').lower()
            proxy_type = self.type_mapping.get(proxy_type_str, default_type)
            
            return ProxyInfo(
                host=str(host),
                port=int(port),
                proxy_type=proxy_type,
                username=data.get('username'),
                password=data.get('password'),
                country=data.get('country'),
                anonymity=data.get('anonymity'),
                source=self.name
            )
        except (ValueError, KeyError) as e:
            self.logger.debug(f"解析JSON代理失败: {e}")
            return None
    
    def _deduplicate_proxies(self, proxies: List[ProxyInfo]) -> List[ProxyInfo]:
        """去重代理列表"""
        seen: Set[str] = set()
        unique_proxies = []
        
        for proxy in proxies:
            # 使用host:port作为唯一标识
            key = f"{proxy.host}:{proxy.port}"
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)
        
        return unique_proxies

class PremiumProxyProvider(ProxyProvider):
    """高级付费代理提供者"""
    
    def __init__(self, service_name: str, api_key: str, api_url: str, config: Dict = None):
        super().__init__(f"Premium_{service_name}")
        self.api_key = api_key
        self.api_url = api_url
        self.config = config or {}
        self.service_name = service_name
    
    async def fetch_proxies(self, limit: int = 100) -> List[ProxyInfo]:
        """从付费API获取代理"""
        try:
            headers = self._build_auth_headers()
            params = self._build_request_params()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(self.api_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_premium_response(data)
                    else:
                        self.logger.error(f"付费代理API请求失败: HTTP {response.status}")
                        return []
        except Exception as e:
            self.logger.error(f"获取付费代理失败: {e}")
            return []
    
    def _build_auth_headers(self) -> Dict[str, str]:
        """构建认证头"""
        auth_format = self.config.get("auth_format", "Bearer {api_key}")
        auth_header = self.config.get("auth_header", "Authorization")
        
        headers = {
            "User-Agent": "ProxyPool/1.0",
            "Accept": "application/json"
        }
        
        if auth_format and auth_header:
            headers[auth_header] = auth_format.format(api_key=self.api_key)
        
        return headers
    
    def _build_request_params(self) -> Dict[str, str]:
        """构建请求参数"""
        params = {}
        
        # 添加通用参数
        if "max_results" in self.config:
            params["limit"] = str(self.config["max_results"])
        
        if "country" in self.config:
            params["country"] = self.config["country"]
        
        if "protocol" in self.config:
            params["protocol"] = self.config["protocol"]
        
        return params
    
    def _parse_premium_response(self, data: Dict) -> List[ProxyInfo]:
        """解析付费代理API响应"""
        proxies = []
        
        # 根据不同服务的响应格式解析
        if self.service_name.lower() == "luminati":
            proxies = self._parse_luminati_response(data)
        elif self.service_name.lower() == "smartproxy":
            proxies = self._parse_smartproxy_response(data)
        elif self.service_name.lower() == "oxylabs":
            proxies = self._parse_oxylabs_response(data)
        else:
            # 通用解析
            proxies = self._parse_generic_response(data)
        
        # 标记为付费代理
        for proxy in proxies:
            proxy.source = self.name
        
        return proxies
    
    def _parse_generic_response(self, data: Dict) -> List[ProxyInfo]:
        """通用响应解析"""
        proxies = []
        
        # 尝试不同的数据结构
        proxy_list = data.get('proxies') or data.get('data') or data.get('results') or []
        
        if isinstance(proxy_list, list):
            for item in proxy_list:
                proxy = self._parse_proxy_item(item)
                if proxy:
                    proxies.append(proxy)
        
        return proxies
    
    def _parse_proxy_item(self, item: Dict) -> Optional[ProxyInfo]:
        """解析单个代理项"""
        try:
            # 尝试不同的字段名
            host = item.get('host') or item.get('ip') or item.get('endpoint')
            port = item.get('port') or item.get('port_http') or item.get('port_socks')
            
            if not host or not port:
                return None
            
            # 解析代理类型
            proxy_type_str = item.get('protocol', 'http').lower()
            proxy_type = ProxyType.HTTP
            
            if 'socks5' in proxy_type_str:
                proxy_type = ProxyType.SOCKS5
            elif 'socks4' in proxy_type_str:
                proxy_type = ProxyType.SOCKS4
            elif 'https' in proxy_type_str:
                proxy_type = ProxyType.HTTPS
            
            return ProxyInfo(
                host=str(host),
                port=int(port),
                proxy_type=proxy_type,
                username=item.get('username'),
                password=item.get('password'),
                country=item.get('country'),
                anonymity=item.get('anonymity_level'),
                source=self.name
            )
        except (ValueError, KeyError) as e:
            self.logger.debug(f"解析代理项失败: {e}")
            return None
    
    def _parse_luminati_response(self, data: Dict) -> List[ProxyInfo]:
        """解析Luminati响应"""
        # Luminati特定的解析逻辑
        return self._parse_generic_response(data)
    
    def _parse_smartproxy_response(self, data: Dict) -> List[ProxyInfo]:
        """解析SmartProxy响应"""
        # SmartProxy特定的解析逻辑
        return self._parse_generic_response(data)
    
    def _parse_oxylabs_response(self, data: Dict) -> List[ProxyInfo]:
        """解析Oxylabs响应"""
        # Oxylabs特定的解析逻辑
        return self._parse_generic_response(data)

class LocalProxyProvider(ProxyProvider):
    """本地代理提供者（从文件读取）"""
    
    def __init__(self, proxy_file: str):
        super().__init__("LocalFile")
        self.proxy_file = proxy_file
    
    async def fetch_proxies(self, limit: int = 100) -> List[ProxyInfo]:
        """从本地文件读取代理"""
        proxies = []
        
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 使用增强解析器
            enhanced_provider = EnhancedFreeProxyProvider()
            proxies = enhanced_provider._parse_simple_list(content, ProxyType.HTTP)
            
            # 标记源
            for proxy in proxies:
                proxy.source = f"LocalFile:{self.proxy_file}"
            
            self.logger.info(f"从本地文件 {self.proxy_file} 读取到 {len(proxies)} 个代理")
            
        except FileNotFoundError:
            self.logger.error(f"代理文件 {self.proxy_file} 不存在")
        except Exception as e:
            self.logger.error(f"读取代理文件失败: {e}")
        
        return proxies

# 工厂函数
def create_proxy_provider(provider_type: str, **kwargs) -> ProxyProvider:
    """创建代理提供者"""
    if provider_type == "free":
        return EnhancedFreeProxyProvider()
    elif provider_type == "premium":
        return PremiumProxyProvider(
            service_name=kwargs.get("service_name", "generic"),
            api_key=kwargs["api_key"],
            api_url=kwargs["api_url"],
            config=kwargs.get("config", {})
        )
    elif provider_type == "local":
        return LocalProxyProvider(kwargs["proxy_file"])
    else:
        raise ValueError(f"不支持的代理提供者类型: {provider_type}")