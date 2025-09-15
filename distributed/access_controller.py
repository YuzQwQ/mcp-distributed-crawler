"""
人性化访问控制器

提供智能延迟机制，模拟真实用户浏览行为，避免对目标服务器造成过大压力。
"""

import asyncio
import random
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse
import logging

@dataclass
class AccessConfig:
    """访问配置"""
    min_delay: float = 0.5  # 最小延迟(秒)
    max_delay: float = 2.0  # 最大延迟(秒)
    base_delay: float = 1.0  # 基础延迟(秒)
    adaptive_delay: bool = True  # 是否启用自适应延迟
    respect_crawl_delay: bool = True  # 是否尊重robots.txt的爬取延迟
    burst_protection: bool = True  # 突发保护

class AccessController:
    """人性化访问控制器"""
    
    def __init__(self, config: Optional[AccessConfig] = None):
        self.config = config or AccessConfig()
        self.logger = logging.getLogger(__name__)
        self.domain_stats: Dict[str, Dict[str, Any]] = {}
        self.last_access: Dict[str, float] = {}
        
    def _get_domain_key(self, url: str) -> str:
        """获取域名键"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return "unknown"
    
    def _calculate_delay(self, domain: str, url: str) -> float:
        """计算合适的延迟时间"""
        
        # 基础随机延迟
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        
        # 自适应延迟：根据历史访问频率调整
        if self.config.adaptive_delay and domain in self.domain_stats:
            stats = self.domain_stats[domain]
            recent_requests = stats.get('recent_requests', 0)
            
            # 如果请求频率高，增加延迟
            if recent_requests > 10:
                delay *= min(2.0, 1.0 + (recent_requests / 20))
            
            # 如果是首次访问，使用较短延迟
            elif recent_requests == 0:
                delay *= 0.8
        
        # 添加轻微随机性，避免模式化
        delay *= random.uniform(0.9, 1.1)
        
        return max(self.config.min_delay, min(self.config.max_delay, delay))
    
    def _update_domain_stats(self, domain: str, response_time: float):
        """更新域名统计信息"""
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {
                'total_requests': 0,
                'recent_requests': 0,
                'avg_response_time': 0.0,
                'last_reset': time.time()
            }
        
        stats = self.domain_stats[domain]
        stats['total_requests'] += 1
        stats['recent_requests'] += 1
        
        # 更新平均响应时间
        old_avg = stats['avg_response_time']
        stats['avg_response_time'] = (old_avg * (stats['total_requests'] - 1) + response_time) / stats['total_requests']
        
        # 每小时重置recent_requests
        if time.time() - stats['last_reset'] > 3600:
            stats['recent_requests'] = 0
            stats['last_reset'] = time.time()
    
    def _respect_rate_limit(self, domain: str) -> float:
        """检查并尊重速率限制"""
        if domain not in self.last_access:
            return 0.0
        
        last_time = self.last_access[domain]
        elapsed = time.time() - last_time
        
        # 确保最小间隔
        min_interval = 0.3  # 300ms最小间隔
        if elapsed < min_interval:
            return min_interval - elapsed
        
        return 0.0
    
    async def wait_before_request(self, url: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        在发送请求前等待合适的时间
        
        Args:
            url: 目标URL
            context: 可选上下文信息
            
        Returns:
            实际等待的时间(秒)
        """
        domain = self._get_domain_key(url)
        
        # 检查速率限制
        rate_limit_delay = self._respect_rate_limit(domain)
        
        # 计算人性化延迟
        human_delay = self._calculate_delay(domain, url)
        
        # 总延迟
        total_delay = max(rate_limit_delay, human_delay)
        
        if total_delay > 0:
            self.logger.info(f"等待 {total_delay:.2f} 秒后访问 {domain}")
            await asyncio.sleep(total_delay)
        
        return total_delay
    
    def record_access(self, url: str, response_time: float = 0.0):
        """记录访问信息"""
        domain = self._get_domain_key(url)
        self.last_access[domain] = time.time()
        self._update_domain_stats(domain, response_time)
    
    def get_domain_stats(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """获取域名统计信息"""
        if domain:
            return self.domain_stats.get(domain, {})
        return self.domain_stats.copy()
    
    def reset_domain_stats(self, domain: Optional[str] = None):
        """重置域名统计"""
        if domain:
            self.domain_stats.pop(domain, None)
            self.last_access.pop(domain, None)
        else:
            self.domain_stats.clear()
            self.last_access.clear()

class GentleCrawlerMixin:
    """温和爬虫混入类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        access_config = kwargs.pop('access_config', None)
        self.access_controller = AccessController(access_config)
    
    async def make_request(self, url: str, **kwargs):
        """发送带人性化延迟的请求"""
        # 等待合适的时间
        wait_time = await self.access_controller.wait_before_request(url)
        
        start_time = time.time()
        try:
            # 这里应该调用实际的HTTP请求
            response = await self._do_request(url, **kwargs)
            
            # 记录访问信息
            response_time = time.time() - start_time
            self.access_controller.record_access(url, response_time)
            
            return response
            
        except Exception as e:
            # 记录失败的访问
            self.access_controller.record_access(url, time.time() - start_time)
            raise
    
    async def _do_request(self, url: str, **kwargs):
        """实际的HTTP请求实现 - 由子类重写"""
        raise NotImplementedError("子类需要实现_do_request方法")

# 全局访问控制器实例
_default_controller = AccessController()

async def gentle_request(url: str, context: Optional[Dict[str, Any]] = None) -> float:
    """
    全局便捷函数：在发送请求前等待
    
    Args:
        url: 目标URL
        context: 可选上下文
        
    Returns:
        等待的时间(秒)
    """
    return await _default_controller.wait_before_request(url, context)