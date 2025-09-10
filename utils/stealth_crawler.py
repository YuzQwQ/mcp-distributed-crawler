"""Stealth爬虫框架

集成Playwright + stealth技术的高级反反爬虫框架。
支持智能重试、代理轮换、反检测和多种爬取策略。
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, List, Optional, Union, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

try:
    from playwright.async_api import Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = BrowserContext = None

# 导入组件
from .playwright_manager import PlaywrightManager, create_playwright_manager
from .crawler_framework import CrawlerFramework
from .proxy_pool import ProxyPool, ProxyInfo
from .enhanced_http_client import EnhancedHttpClient

logger = logging.getLogger(__name__)

@dataclass
class CrawlResult:
    """爬取结果数据类"""
    url: str
    success: bool
    content: Optional[str] = None
    status_code: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    response_time: Optional[float] = None
    proxy_used: Optional[str] = None
    stealth_applied: bool = False
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
        return result

class AntiDetectionStrategy:
    """反检测策略类"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 检测规则
        self.detection_patterns = {
            "cloudflare": ["cloudflare", "cf-ray", "checking your browser"],
            "captcha": ["captcha", "recaptcha", "hcaptcha", "verify you are human"],
            "rate_limit": ["rate limit", "too many requests", "429"],
            "blocked": ["access denied", "forbidden", "blocked", "403"],
            "bot_detection": ["bot detected", "automated traffic", "suspicious activity"]
        }
        
        # 应对策略
        self.strategies = {
            "cloudflare": self._handle_cloudflare,
            "captcha": self._handle_captcha,
            "rate_limit": self._handle_rate_limit,
            "blocked": self._handle_blocked,
            "bot_detection": self._handle_bot_detection
        }
        
    def detect_anti_crawler(self, content: str, status_code: int, headers: Dict[str, str]) -> Optional[str]:
        """检测反爬虫机制"""
        content_lower = content.lower()
        
        # 检查状态码
        if status_code in [403, 429, 503]:
            if status_code == 429:
                return "rate_limit"
            elif status_code == 403:
                return "blocked"
            elif status_code == 503:
                return "cloudflare"
                
        # 检查响应头
        for key, value in headers.items():
            key_lower = key.lower()
            value_lower = str(value).lower()
            
            if "cloudflare" in key_lower or "cf-" in key_lower:
                return "cloudflare"
            if "captcha" in value_lower:
                return "captcha"
                
        # 检查内容
        for detection_type, patterns in self.detection_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    return detection_type
                    
        return None
        
    async def handle_detection(self, detection_type: str, page: Page, manager: PlaywrightManager) -> bool:
        """处理检测到的反爬虫机制"""
        if detection_type in self.strategies:
            return await self.strategies[detection_type](page, manager)
        return False
        
    async def _handle_cloudflare(self, page: Page, manager: PlaywrightManager) -> bool:
        """处理Cloudflare检测"""
        try:
            logger.info("检测到Cloudflare，等待验证完成...")
            
            # 等待Cloudflare验证完成
            await asyncio.sleep(5)
            
            # 检查是否有验证按钮
            verify_button = await page.query_selector("input[type='button'][value*='Verify']") or \
                           await page.query_selector(".cf-browser-verification")
                           
            if verify_button:
                await verify_button.click()
                await asyncio.sleep(3)
                
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            # 检查是否成功绕过
            current_url = page.url
            if "challenge" not in current_url.lower():
                logger.info("Cloudflare验证成功")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"处理Cloudflare失败: {e}")
            return False
            
    async def _handle_captcha(self, page: Page, manager: PlaywrightManager) -> bool:
        """处理验证码"""
        logger.warning("检测到验证码，需要人工处理")
        return False
        
    async def _handle_rate_limit(self, page: Page, manager: PlaywrightManager) -> bool:
        """处理频率限制"""
        logger.info("检测到频率限制，等待并轮换代理...")
        
        # 等待一段时间
        await asyncio.sleep(random.uniform(10, 30))
        
        # 轮换代理
        await manager._rotate_proxy()
        
        return True
        
    async def _handle_blocked(self, page: Page, manager: PlaywrightManager) -> bool:
        """处理IP封禁"""
        logger.info("检测到IP封禁，轮换代理...")
        
        # 轮换代理
        await manager._rotate_proxy()
        
        return True
        
    async def _handle_bot_detection(self, page: Page, manager: PlaywrightManager) -> bool:
        """处理机器人检测"""
        logger.info("检测到机器人识别，应用额外反检测措施...")
        
        # 模拟人类行为
        await self._simulate_human_behavior(page)
        
        return True
        
    async def _simulate_human_behavior(self, page: Page):
        """模拟人类行为"""
        try:
            # 随机鼠标移动
            await page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600)
            )
            
            # 随机滚动
            await page.evaluate(f"window.scrollTo(0, {random.randint(100, 500)})")
            await asyncio.sleep(random.uniform(1, 3))
            
            # 随机点击（如果有安全的元素）
            safe_elements = await page.query_selector_all("body, html")
            if safe_elements:
                element = random.choice(safe_elements)
                await element.click()
                
        except Exception as e:
            logger.debug(f"模拟人类行为失败: {e}")

class StealthCrawler:
    """Stealth爬虫主类"""
    
    def __init__(self, config: Dict = None, proxy_pool_config: Dict = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright未安装，请运行: pip install playwright playwright-stealth")
            
        self.config = config or {}
        self.proxy_pool_config = proxy_pool_config or {}
        
        # 组件初始化
        self.playwright_manager: Optional[PlaywrightManager] = None
        self.fallback_client: Optional[EnhancedHttpClient] = None
        self.anti_detection = AntiDetectionStrategy(self.config.get("anti_detection", {}))
        
        # 配置参数
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)
        self.use_fallback = self.config.get("use_fallback", True)
        self.concurrent_limit = self.config.get("concurrent_limit", 5)
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "stealth_bypasses": 0,
            "fallback_uses": 0,
            "anti_crawler_detections": 0,
            "start_time": datetime.now()
        }
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(self.concurrent_limit)
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def start(self):
        """启动爬虫"""
        try:
            # 启动Playwright管理器
            playwright_config = self.config.get("playwright", {})
            self.playwright_manager = create_playwright_manager(playwright_config, self.proxy_pool_config)
            await self.playwright_manager.start()
            
            # 初始化备用HTTP客户端
            if self.use_fallback:
                fallback_config = self.config.get("fallback_http", {})
                self.fallback_client = EnhancedHttpClient(fallback_config)
                
            logger.info("Stealth爬虫启动成功")
            
        except Exception as e:
            logger.error(f"启动Stealth爬虫失败: {e}")
            raise
            
    async def close(self):
        """关闭爬虫"""
        try:
            if self.playwright_manager:
                await self.playwright_manager.close()
                
            if self.fallback_client:
                await self.fallback_client.close()
                
            logger.info("Stealth爬虫已关闭")
            
        except Exception as e:
            logger.error(f"关闭Stealth爬虫失败: {e}")
            
    async def crawl_url(self, url: str, **kwargs) -> CrawlResult:
        """爬取单个URL"""
        async with self.semaphore:
            return await self._crawl_url_internal(url, **kwargs)
            
    async def _crawl_url_internal(self, url: str, **kwargs) -> CrawlResult:
        """内部爬取方法"""
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        result = CrawlResult(
            url=url,
            success=False,
            timestamp=datetime.now()
        )
        
        # 尝试使用Playwright
        for attempt in range(self.max_retries + 1):
            try:
                playwright_result = await self._crawl_with_playwright(url, **kwargs)
                if playwright_result.success:
                    result = playwright_result
                    result.stealth_applied = True
                    break
                    
                # 检测反爬虫机制
                if playwright_result.content:
                    detection = self.anti_detection.detect_anti_crawler(
                        playwright_result.content,
                        playwright_result.status_code or 0,
                        playwright_result.headers or {}
                    )
                    
                    if detection:
                        self.stats["anti_crawler_detections"] += 1
                        logger.info(f"检测到反爬虫机制: {detection}")
                        
                        # 尝试处理
                        if attempt < self.max_retries:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                            
            except Exception as e:
                logger.warning(f"Playwright爬取失败 (尝试 {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    result.error = str(e)
                    
        # 如果Playwright失败，尝试备用HTTP客户端
        if not result.success and self.use_fallback and self.fallback_client:
            try:
                fallback_result = await self._crawl_with_fallback(url, **kwargs)
                if fallback_result.success:
                    result = fallback_result
                    self.stats["fallback_uses"] += 1
                    
            except Exception as e:
                logger.warning(f"备用HTTP客户端爬取失败: {e}")
                
        # 更新统计
        result.response_time = time.time() - start_time
        if result.success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
            
        return result
        
    async def _crawl_with_playwright(self, url: str, **kwargs) -> CrawlResult:
        """使用Playwright爬取"""
        page = None
        try:
            # 创建页面
            page = await self.playwright_manager.create_page()
            
            # 导航到URL
            response = await page.goto(url, **kwargs)
            
            # 等待页面加载
            wait_for = kwargs.get("wait_for")
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=kwargs.get("timeout", 30000))
            else:
                await page.wait_for_load_state("networkidle", timeout=30000)
                
            # 获取页面内容
            content = await page.content()
            
            # 获取响应信息
            status_code = response.status if response else 200
            headers = dict(response.headers) if response else {}
            
            return CrawlResult(
                url=url,
                success=True,
                content=content,
                status_code=status_code,
                headers=headers,
                timestamp=datetime.now(),
                proxy_used=self.playwright_manager.current_proxy.host if self.playwright_manager.current_proxy else None
            )
            
        except Exception as e:
            return CrawlResult(
                url=url,
                success=False,
                error=str(e),
                timestamp=datetime.now()
            )
            
        finally:
            if page and not page.is_closed():
                await page.close()
                if page in self.playwright_manager.pages:
                    self.playwright_manager.pages.remove(page)
                    
    async def _crawl_with_fallback(self, url: str, **kwargs) -> CrawlResult:
        """使用备用HTTP客户端爬取"""
        try:
            response = await self.fallback_client.get(url, **kwargs)
            
            return CrawlResult(
                url=url,
                success=response.status_code < 400,
                content=response.text,
                status_code=response.status_code,
                headers=dict(response.headers),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return CrawlResult(
                url=url,
                success=False,
                error=str(e),
                timestamp=datetime.now()
            )
            
    async def crawl_urls(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """批量爬取URL"""
        tasks = [self.crawl_url(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(CrawlResult(
                    url=urls[i],
                    success=False,
                    error=str(result),
                    timestamp=datetime.now()
                ))
            else:
                processed_results.append(result)
                
        return processed_results
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        runtime = datetime.now() - self.stats["start_time"]
        
        stats = {
            **self.stats,
            "runtime_seconds": runtime.total_seconds(),
            "success_rate": (self.stats["successful_requests"] / max(self.stats["total_requests"], 1)) * 100,
            "fallback_rate": (self.stats["fallback_uses"] / max(self.stats["total_requests"], 1)) * 100,
            "detection_rate": (self.stats["anti_crawler_detections"] / max(self.stats["total_requests"], 1)) * 100
        }
        
        # 添加Playwright管理器统计
        if self.playwright_manager:
            playwright_stats = self.playwright_manager.get_stats()
            stats["playwright"] = playwright_stats
            
        return stats
        
    async def save_results(self, results: List[CrawlResult], output_file: str):
        """保存爬取结果"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为字典格式
            data = {
                "timestamp": datetime.now().isoformat(),
                "stats": self.get_stats(),
                "results": [result.to_dict() for result in results]
            }
            
            # 保存到文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"爬取结果已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            
# 工厂函数
def create_stealth_crawler(config: Dict = None, proxy_pool_config: Dict = None) -> StealthCrawler:
    """创建Stealth爬虫"""
    return StealthCrawler(config, proxy_pool_config)
    
# 便捷函数
async def stealth_crawl(urls: Union[str, List[str]], config: Dict = None, 
                       proxy_pool_config: Dict = None, **kwargs) -> Union[CrawlResult, List[CrawlResult]]:
    """便捷的stealth爬取函数"""
    async with create_stealth_crawler(config, proxy_pool_config) as crawler:
        if isinstance(urls, str):
            return await crawler.crawl_url(urls, **kwargs)
        else:
            return await crawler.crawl_urls(urls, **kwargs)
            
if __name__ == "__main__":
    # 测试代码
    async def test_stealth_crawler():
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False
            },
            "max_retries": 2,
            "concurrent_limit": 3
        }
        
        test_urls = [
            "https://httpbin.org/user-agent",
            "https://httpbin.org/headers",
            "https://httpbin.org/ip"
        ]
        
        results = await stealth_crawl(test_urls, config)
        
        for result in results:
            print(f"URL: {result.url}")
            print(f"成功: {result.success}")
            print(f"状态码: {result.status_code}")
            print(f"响应时间: {result.response_time:.2f}s")
            print(f"Stealth应用: {result.stealth_applied}")
            print("-" * 50)
            
    asyncio.run(test_stealth_crawler())