"""Playwright浏览器管理器

集成Playwright和stealth技术的反反爬虫浏览器管理器。
支持多浏览器、代理轮换、反检测和智能重试。
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Union, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
    from playwright_stealth import stealth
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = BrowserContext = Page = Playwright = None
    stealth = None

# 导入代理池组件
from .proxy_pool import ProxyPool, ProxyInfo, ProxyStatus
from .proxy_providers import create_proxy_provider
from .proxy_validator import create_proxy_validator
from .proxy_rotator import create_proxy_rotator

logger = logging.getLogger(__name__)

class BrowserConfig:
    """浏览器配置类"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 基础配置
        self.browser_type = self.config.get("browser_type", "chromium")  # chromium, firefox, webkit
        self.headless = self.config.get("headless", True)
        self.user_data_dir = self.config.get("user_data_dir", None)
        
        # 窗口配置
        self.viewport = self.config.get("viewport", {"width": 1920, "height": 1080})
        self.device_scale_factor = self.config.get("device_scale_factor", 1)
        
        # 代理配置
        self.use_proxy_pool = self.config.get("use_proxy_pool", True)
        self.proxy_rotation_interval = self.config.get("proxy_rotation_interval", 10)  # 请求数
        
        # Stealth配置
        self.enable_stealth = self.config.get("enable_stealth", True)
        self.stealth_config = self.config.get("stealth_config", {
            "chrome_app": True,
            "chrome_csi": True,
            "chrome_load_times": True,
            "chrome_runtime": True,
            "iframe_content_window": True,
            "media_codecs": True,
            "navigator_languages": True,
            "navigator_permissions": True,
            "navigator_plugins": True,
            "navigator_vendor": True,
            "navigator_webdriver": True,
            "hairline": True
        })
        
        # 反检测配置
        self.anti_detection = self.config.get("anti_detection", {
            "random_user_agent": True,
            "random_viewport": True,
            "random_timezone": True,
            "block_webrtc": True,
            "block_canvas_fingerprint": True,
            "random_fonts": True
        })
        
        # 性能配置
        self.max_concurrent_pages = self.config.get("max_concurrent_pages", 5)
        self.page_timeout = self.config.get("page_timeout", 30000)  # 毫秒
        self.navigation_timeout = self.config.get("navigation_timeout", 30000)
        
        # 资源优化
        self.block_resources = self.config.get("block_resources", ["image", "font", "media"])
        self.block_ads = self.config.get("block_ads", True)
        
        # 重试配置
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)
        
class PlaywrightManager:
    """Playwright浏览器管理器"""
    
    def __init__(self, config: Dict = None, proxy_pool_config: Dict = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright未安装，请运行: pip install playwright playwright-stealth")
            
        self.config = BrowserConfig(config)
        self.proxy_pool_config = proxy_pool_config or {}
        
        # 浏览器实例
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: List[BrowserContext] = []
        self.pages: List[Page] = []
        
        # 代理池管理
        self.proxy_pool: Optional[ProxyPool] = None
        self.current_proxy: Optional[ProxyInfo] = None
        self.proxy_request_count = 0
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxy_switches": 0,
            "stealth_bypasses": 0,
            "start_time": datetime.now()
        }
        
        # 用户代理池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
        ]
        
        # 视口尺寸池
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720}
        ]
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def start(self):
        """启动浏览器管理器"""
        try:
            # 初始化代理池
            if self.config.use_proxy_pool:
                await self._init_proxy_pool()
                
            # 启动Playwright
            self.playwright = await async_playwright().start()
            
            # 创建浏览器实例
            await self._create_browser()
            
            logger.info(f"Playwright管理器启动成功，浏览器类型: {self.config.browser_type}")
            
        except Exception as e:
            logger.error(f"启动Playwright管理器失败: {e}")
            raise
            
    async def close(self):
        """关闭浏览器管理器"""
        try:
            # 关闭所有页面
            for page in self.pages:
                if not page.is_closed():
                    await page.close()
                    
            # 关闭所有上下文
            for context in self.contexts:
                await context.close()
                
            # 关闭浏览器
            if self.browser:
                await self.browser.close()
                
            # 关闭Playwright
            if self.playwright:
                await self.playwright.stop()
                
            # 关闭代理池
            if self.proxy_pool:
                await self.proxy_pool.close()
                
            logger.info("Playwright管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭Playwright管理器失败: {e}")
            
    async def _init_proxy_pool(self):
        """初始化代理池"""
        try:
            # 创建代理提供者
            providers = []
            if self.proxy_pool_config.get("use_free_proxies", True):
                providers.append(create_proxy_provider("free", self.proxy_pool_config.get("free_config", {})))
            if self.proxy_pool_config.get("use_local_proxies", False):
                providers.append(create_proxy_provider("local", self.proxy_pool_config.get("local_config", {})))
                
            # 创建验证器
            validator = create_proxy_validator("enhanced", self.proxy_pool_config.get("validator_config", {}))
            
            # 创建轮换器
            rotator = create_proxy_rotator("adaptive", self.proxy_pool_config.get("rotator_config", {}))
            
            # 创建代理池
            self.proxy_pool = ProxyPool(
                providers=providers,
                validator=validator,
                rotator=rotator,
                config=self.proxy_pool_config
            )
            
            # 启动代理池
            await self.proxy_pool.start()
            
            logger.info("代理池初始化成功")
            
        except Exception as e:
            logger.error(f"初始化代理池失败: {e}")
            raise
            
    async def _create_browser(self):
        """创建浏览器实例"""
        try:
            # 获取浏览器类型
            if self.config.browser_type == "chromium":
                browser_type = self.playwright.chromium
            elif self.config.browser_type == "firefox":
                browser_type = self.playwright.firefox
            elif self.config.browser_type == "webkit":
                browser_type = self.playwright.webkit
            else:
                raise ValueError(f"不支持的浏览器类型: {self.config.browser_type}")
                
            # 浏览器启动参数
            launch_options = {
                "headless": self.config.headless,
                "args": self._get_browser_args()
            }
            
            # 添加用户数据目录
            if self.config.user_data_dir:
                launch_options["user_data_dir"] = self.config.user_data_dir
                
            # 启动浏览器
            self.browser = await browser_type.launch(**launch_options)
            
            logger.info(f"浏览器启动成功: {self.config.browser_type}")
            
        except Exception as e:
            logger.error(f"创建浏览器失败: {e}")
            raise
            
    def _get_browser_args(self) -> List[str]:
        """获取浏览器启动参数"""
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection"
        ]
        
        # 反检测参数
        if self.config.anti_detection.get("block_webrtc", True):
            args.extend([
                "--disable-webrtc",
                "--disable-webrtc-multiple-routes",
                "--disable-webrtc-hw-decoding",
                "--disable-webrtc-hw-encoding"
            ])
            
        return args
        
    async def create_context(self, proxy: Optional[ProxyInfo] = None) -> BrowserContext:
        """创建浏览器上下文"""
        try:
            # 上下文选项
            context_options = {
                "viewport": self._get_random_viewport() if self.config.anti_detection.get("random_viewport") else self.config.viewport,
                "user_agent": self._get_random_user_agent() if self.config.anti_detection.get("random_user_agent") else None,
                "locale": "zh-CN",
                "timezone_id": self._get_random_timezone() if self.config.anti_detection.get("random_timezone") else "Asia/Shanghai",
                "permissions": ["geolocation"],
                "geolocation": {"latitude": 39.9042, "longitude": 116.4074},  # 北京
                "color_scheme": "light",
                "reduced_motion": "reduce"
            }
            
            # 添加代理配置
            if proxy:
                context_options["proxy"] = {
                    "server": f"{proxy.protocol}://{proxy.host}:{proxy.port}"
                }
                if proxy.username and proxy.password:
                    context_options["proxy"]["username"] = proxy.username
                    context_options["proxy"]["password"] = proxy.password
                    
            # 创建上下文
            context = await self.browser.new_context(**context_options)
            
            # 设置额外的反检测措施
            await self._setup_anti_detection(context)
            
            self.contexts.append(context)
            return context
            
        except Exception as e:
            logger.error(f"创建浏览器上下文失败: {e}")
            raise
            
    async def create_page(self, context: Optional[BrowserContext] = None, enable_stealth: bool = None) -> Page:
        """创建页面"""
        try:
            # 检查并发限制
            if len(self.pages) >= self.config.max_concurrent_pages:
                # 关闭最旧的页面
                oldest_page = self.pages.pop(0)
                if not oldest_page.is_closed():
                    await oldest_page.close()
                    
            # 获取或创建上下文
            if not context:
                # 获取代理
                proxy = await self._get_proxy() if self.config.use_proxy_pool else None
                context = await self.create_context(proxy)
                
            # 创建页面
            page = await context.new_page()
            
            # 设置超时
            page.set_default_timeout(self.config.page_timeout)
            page.set_default_navigation_timeout(self.config.navigation_timeout)
            
            # 启用stealth
            if enable_stealth is None:
                enable_stealth = self.config.enable_stealth
                
            if enable_stealth:
                await self._apply_stealth(page)
                
            # 设置资源拦截
            await self._setup_resource_blocking(page)
            
            # 设置请求拦截
            await self._setup_request_interception(page)
            
            self.pages.append(page)
            return page
            
        except Exception as e:
            logger.error(f"创建页面失败: {e}")
            raise
            
    async def _apply_stealth(self, page: Page):
        """应用stealth反检测"""
        try:
            # 使用playwright_stealth的Stealth类
            stealth_obj = stealth.Stealth(**self.config.stealth_config)
            await stealth_obj.apply_stealth_async(page)
            
            # 额外的反检测脚本
            await page.add_init_script("""
                // 隐藏webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // 修改plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // 修改languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
                
                // 隐藏自动化特征
                window.chrome = {
                    runtime: {},
                };
                
                // 防止canvas指纹
                const getContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(type) {
                    if (type === '2d') {
                        const context = getContext.call(this, type);
                        const getImageData = context.getImageData;
                        context.getImageData = function(x, y, w, h) {
                            const imageData = getImageData.call(this, x, y, w, h);
                            for (let i = 0; i < imageData.data.length; i += 4) {
                                imageData.data[i] += Math.floor(Math.random() * 10) - 5;
                                imageData.data[i + 1] += Math.floor(Math.random() * 10) - 5;
                                imageData.data[i + 2] += Math.floor(Math.random() * 10) - 5;
                            }
                            return imageData;
                        };
                        return context;
                    }
                    return getContext.call(this, type);
                };
            """)
            
            self.stats["stealth_bypasses"] += 1
            logger.debug("Stealth反检测已应用")
            
        except Exception as e:
            logger.error(f"应用stealth失败: {e}")
            
    async def _setup_anti_detection(self, context: BrowserContext):
        """设置反检测措施"""
        try:
            # 添加初始化脚本
            await context.add_init_script("""
                // 删除webdriver标识
                delete navigator.__proto__.webdriver;
                
                // 修改权限查询
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // 修改插件检测
                Object.defineProperty(navigator, 'plugins', {
                    get: function() {
                        return {
                            0: {
                                name: 'Chrome PDF Plugin',
                                filename: 'internal-pdf-viewer',
                                description: 'Portable Document Format'
                            },
                            1: {
                                name: 'Chrome PDF Viewer',
                                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                                description: ''
                            },
                            2: {
                                name: 'Native Client',
                                filename: 'internal-nacl-plugin',
                                description: ''
                            },
                            length: 3
                        };
                    }
                });
            """)
            
        except Exception as e:
            logger.error(f"设置反检测措施失败: {e}")
            
    async def _setup_resource_blocking(self, page: Page):
        """设置资源拦截"""
        try:
            if self.config.block_resources:
                await page.route("**/*", self._handle_route)
                
        except Exception as e:
            logger.error(f"设置资源拦截失败: {e}")
            
    async def _handle_route(self, route):
        """处理路由拦截"""
        try:
            resource_type = route.request.resource_type
            url = route.request.url
            
            # 拦截指定类型的资源
            if resource_type in self.config.block_resources:
                await route.abort()
                return
                
            # 拦截广告
            if self.config.block_ads and self._is_ad_url(url):
                await route.abort()
                return
                
            # 继续请求
            await route.continue_()
            
        except Exception as e:
            logger.error(f"处理路由拦截失败: {e}")
            await route.continue_()
            
    def _is_ad_url(self, url: str) -> bool:
        """检查是否为广告URL"""
        ad_domains = [
            "doubleclick.net", "googleadservices.com", "googlesyndication.com",
            "googletagmanager.com", "google-analytics.com", "facebook.com/tr",
            "scorecardresearch.com", "quantserve.com", "outbrain.com"
        ]
        
        return any(domain in url for domain in ad_domains)
        
    async def _setup_request_interception(self, page: Page):
        """设置请求拦截"""
        try:
            # 监听请求
            page.on("request", self._on_request)
            page.on("response", self._on_response)
            
        except Exception as e:
            logger.error(f"设置请求拦截失败: {e}")
            
    def _on_request(self, request):
        """请求事件处理"""
        self.stats["total_requests"] += 1
        self.proxy_request_count += 1
        
        # 检查是否需要轮换代理
        if (self.config.use_proxy_pool and 
            self.proxy_request_count >= self.config.proxy_rotation_interval):
            asyncio.create_task(self._rotate_proxy())
            
    def _on_response(self, response):
        """响应事件处理"""
        if response.status < 400:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
            
    async def _get_proxy(self) -> Optional[ProxyInfo]:
        """获取代理"""
        try:
            if not self.proxy_pool:
                return None
                
            proxy = await self.proxy_pool.get_proxy()
            if proxy:
                self.current_proxy = proxy
                return proxy
                
            return None
            
        except Exception as e:
            logger.error(f"获取代理失败: {e}")
            return None
            
    async def _rotate_proxy(self):
        """轮换代理"""
        try:
            if not self.proxy_pool:
                return
                
            # 获取新代理
            new_proxy = await self._get_proxy()
            if new_proxy and new_proxy != self.current_proxy:
                self.current_proxy = new_proxy
                self.proxy_request_count = 0
                self.stats["proxy_switches"] += 1
                logger.info(f"代理已轮换: {new_proxy.host}:{new_proxy.port}")
                
        except Exception as e:
            logger.error(f"轮换代理失败: {e}")
            
    def _get_random_user_agent(self) -> str:
        """获取随机用户代理"""
        return random.choice(self.user_agents)
        
    def _get_random_viewport(self) -> Dict[str, int]:
        """获取随机视口"""
        return random.choice(self.viewports)
        
    def _get_random_timezone(self) -> str:
        """获取随机时区"""
        timezones = [
            "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Tokyo",
            "America/New_York", "Europe/London", "America/Los_Angeles"
        ]
        return random.choice(timezones)
        
    async def navigate_with_retry(self, page: Page, url: str, **kwargs) -> bool:
        """带重试的页面导航"""
        for attempt in range(self.config.max_retries + 1):
            try:
                await page.goto(url, **kwargs)
                return True
                
            except Exception as e:
                logger.warning(f"导航失败 (尝试 {attempt + 1}/{self.config.max_retries + 1}): {e}")
                
                if attempt < self.config.max_retries:
                    # 等待重试
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    
                    # 尝试轮换代理
                    if self.config.use_proxy_pool:
                        await self._rotate_proxy()
                        
                else:
                    logger.error(f"导航最终失败: {url}")
                    return False
                    
        return False
        
    async def get_page_content(self, url: str, wait_for: Optional[str] = None, 
                              timeout: Optional[int] = None) -> Optional[str]:
        """获取页面内容"""
        page = None
        try:
            # 创建页面
            page = await self.create_page()
            
            # 导航到URL
            success = await self.navigate_with_retry(page, url, timeout=timeout or self.config.navigation_timeout)
            if not success:
                return None
                
            # 等待特定元素
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout or self.config.page_timeout)
                
            # 获取页面内容
            content = await page.content()
            return content
            
        except Exception as e:
            logger.error(f"获取页面内容失败: {e}")
            return None
            
        finally:
            if page and not page.is_closed():
                await page.close()
                if page in self.pages:
                    self.pages.remove(page)
                    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        runtime = datetime.now() - self.stats["start_time"]
        
        return {
            **self.stats,
            "runtime_seconds": runtime.total_seconds(),
            "success_rate": (self.stats["successful_requests"] / max(self.stats["total_requests"], 1)) * 100,
            "active_pages": len(self.pages),
            "active_contexts": len(self.contexts),
            "current_proxy": f"{self.current_proxy.host}:{self.current_proxy.port}" if self.current_proxy else None
        }
        
# 工厂函数
def create_playwright_manager(config: Dict = None, proxy_pool_config: Dict = None) -> PlaywrightManager:
    """创建Playwright管理器"""
    return PlaywrightManager(config, proxy_pool_config)
    
async def test_playwright_manager():
    """测试Playwright管理器"""
    config = {
        "browser_type": "chromium",
        "headless": True,
        "enable_stealth": True,
        "use_proxy_pool": False,  # 测试时禁用代理池
        "max_concurrent_pages": 3
    }
    
    async with create_playwright_manager(config) as manager:
        # 测试页面创建和内容获取
        content = await manager.get_page_content("https://httpbin.org/user-agent")
        if content:
            print("页面内容获取成功")
            print(f"内容长度: {len(content)}")
        else:
            print("页面内容获取失败")
            
        # 打印统计信息
        stats = manager.get_stats()
        print(f"统计信息: {stats}")
        
if __name__ == "__main__":
    asyncio.run(test_playwright_manager())