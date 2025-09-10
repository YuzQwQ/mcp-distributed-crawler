#!/usr/bin/env python3
"""Stealth爬虫系统演示脚本

展示Playwright + stealth反反爬虫系统的完整功能：
- 基础stealth爬取
- 代理池集成
- 批量并发爬取
- 反检测策略
- 智能重试机制
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入组件
try:
    from utils.stealth_crawler import StealthCrawler, create_stealth_crawler, stealth_crawl
    from utils.playwright_manager import PlaywrightManager, create_playwright_manager
    from utils.proxy_pool import ProxyPool
    STEALTH_AVAILABLE = True
except ImportError as e:
    logger.error(f"导入Stealth爬虫组件失败: {e}")
    STEALTH_AVAILABLE = False

class StealthCrawlerDemo:
    """Stealth爬虫演示器"""
    
    def __init__(self):
        self.demo_urls = {
            "basic_test": [
                "https://httpbin.org/user-agent",
                "https://httpbin.org/headers",
                "https://httpbin.org/ip"
            ],
            "detection_test": [
                "https://bot.sannysoft.com/",
                "https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html"
            ],
            "real_world": [
                "https://quotes.toscrape.com/",
                "https://books.toscrape.com/",
                "https://httpbin.org/delay/2"
            ]
        }
        
    async def run_demo(self):
        """运行完整演示"""
        if not STEALTH_AVAILABLE:
            print("❌ Stealth爬虫组件不可用，请安装: pip install playwright playwright-stealth")
            return
            
        print("🚀 Stealth爬虫系统演示开始")
        print("=" * 60)
        
        # 演示项目
        demos = [
            ("基础Stealth爬取", self.demo_basic_stealth),
            ("批量并发爬取", self.demo_batch_crawling),
            ("反检测功能", self.demo_anti_detection),
            ("代理集成", self.demo_proxy_integration),
            ("智能重试机制", self.demo_smart_retry),
            ("实际应用场景", self.demo_real_world_usage)
        ]
        
        for demo_name, demo_func in demos:
            print(f"\n📋 {demo_name}")
            print("-" * 40)
            try:
                await demo_func()
                print(f"✅ {demo_name} 演示完成")
            except Exception as e:
                print(f"❌ {demo_name} 演示失败: {e}")
                logger.error(f"演示 {demo_name} 失败: {e}")
                
        print("\n🎉 Stealth爬虫系统演示结束")
        
    async def demo_basic_stealth(self):
        """演示基础stealth爬取"""
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False
            },
            "max_retries": 2
        }
        
        print("🔍 测试基础stealth爬取功能...")
        
        # 单个URL爬取
        result = await stealth_crawl("https://httpbin.org/user-agent", config)
        
        if result.success:
            print(f"✅ 成功爬取: {result.url}")
            print(f"   状态码: {result.status_code}")
            print(f"   内容长度: {len(result.content) if result.content else 0} 字符")
            print(f"   响应时间: {result.response_time:.2f}秒")
            print(f"   Stealth应用: {'是' if result.stealth_applied else '否'}")
            
            # 解析User-Agent信息
            if result.content:
                try:
                    import json
                    data = json.loads(result.content)
                    user_agent = data.get('user-agent', '')
                    print(f"   User-Agent: {user_agent[:80]}...")
                except:
                    pass
        else:
            print(f"❌ 爬取失败: {result.error}")
            
    async def demo_batch_crawling(self):
        """演示批量并发爬取"""
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False
            },
            "concurrent_limit": 3,
            "max_retries": 1
        }
        
        print("🔄 测试批量并发爬取功能...")
        
        # 批量爬取
        start_time = asyncio.get_event_loop().time()
        results = await stealth_crawl(self.demo_urls["basic_test"], config)
        end_time = asyncio.get_event_loop().time()
        
        successful_count = sum(1 for r in results if r.success)
        total_time = end_time - start_time
        
        print(f"✅ 批量爬取完成:")
        print(f"   总URL数: {len(results)}")
        print(f"   成功数: {successful_count}")
        print(f"   成功率: {(successful_count/len(results)*100):.1f}%")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均速度: {len(results)/total_time:.2f} URL/秒")
        
        # 显示详细结果
        for i, result in enumerate(results, 1):
            status = "✅" if result.success else "❌"
            print(f"   {i}. {status} {result.url} ({result.status_code if result.success else result.error})")
            
    async def demo_anti_detection(self):
        """演示反检测功能"""
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False,
                "anti_detection": {
                    "random_user_agent": True,
                    "random_viewport": True,
                    "block_webrtc": True,
                    "block_canvas_fingerprint": True
                }
            },
            "max_retries": 1
        }
        
        print("🛡️ 测试反检测功能...")
        
        # 测试反检测URL
        test_url = "https://bot.sannysoft.com/"
        
        try:
            result = await stealth_crawl(test_url, config, timeout=15000)
            
            if result.success:
                print(f"✅ 反检测测试成功:")
                print(f"   URL: {result.url}")
                print(f"   状态码: {result.status_code}")
                print(f"   响应时间: {result.response_time:.2f}秒")
                print(f"   Stealth应用: {'是' if result.stealth_applied else '否'}")
                
                # 分析页面内容中的检测结果
                if result.content and len(result.content) > 100:
                    print(f"   页面内容长度: {len(result.content)} 字符")
                    print("   🔍 页面成功加载，可能绕过了部分检测")
                else:
                    print("   ⚠️ 页面内容较少，可能被检测到")
            else:
                print(f"❌ 反检测测试失败: {result.error}")
                
        except Exception as e:
            print(f"⚠️ 反检测测试异常: {e}")
            
    async def demo_proxy_integration(self):
        """演示代理集成"""
        # 检查是否有代理文件
        proxy_file = Path("proxy_list.txt")
        if not proxy_file.exists():
            print("⚠️ 未找到代理文件 proxy_list.txt，跳过代理演示")
            print("   提示: 创建 proxy_list.txt 文件，每行一个代理地址 (格式: ip:port)")
            return
            
        proxy_config = {
            "use_free_proxies": False,
            "use_local_proxies": True,
            "local_config": {
                "proxy_file": "proxy_list.txt"
            }
        }
        
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": True,
                "proxy_rotation_interval": 2
            },
            "max_retries": 1
        }
        
        print("🌐 测试代理集成功能...")
        
        try:
            async with create_stealth_crawler(config, proxy_config) as crawler:
                # 测试多个URL以触发代理轮换
                results = await crawler.crawl_urls(self.demo_urls["basic_test"][:2])
                
                stats = crawler.get_stats()
                
                print(f"✅ 代理集成测试完成:")
                print(f"   爬取结果数: {len(results)}")
                print(f"   代理切换次数: {stats.get('playwright', {}).get('proxy_switches', 0)}")
                print(f"   成功率: {(sum(1 for r in results if r.success)/len(results)*100):.1f}%")
                
                for i, result in enumerate(results, 1):
                    status = "✅" if result.success else "❌"
                    proxy_info = f" (代理: {result.proxy_used})" if result.proxy_used else ""
                    print(f"   {i}. {status} {result.url}{proxy_info}")
                    
        except Exception as e:
            print(f"❌ 代理集成测试失败: {e}")
            
    async def demo_smart_retry(self):
        """演示智能重试机制"""
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False
            },
            "max_retries": 3,
            "retry_delay": 1,
            "use_fallback": True
        }
        
        print("🔄 测试智能重试机制...")
        
        # 测试一个可能失败的URL
        test_urls = [
            "https://httpbin.org/status/500",  # 服务器错误
            "https://httpbin.org/delay/10",    # 超时测试
            "https://nonexistent-domain-12345.com"  # 不存在的域名
        ]
        
        for url in test_urls:
            print(f"\n   测试URL: {url}")
            try:
                result = await stealth_crawl(url, config, timeout=5000)
                
                print(f"   结果: {'成功' if result.success else '失败'}")
                print(f"   重试次数: {result.retry_count}")
                print(f"   响应时间: {result.response_time:.2f}秒")
                if result.error:
                    print(f"   错误信息: {result.error[:100]}...")
                    
            except Exception as e:
                print(f"   异常: {e}")
                
    async def demo_real_world_usage(self):
        """演示实际应用场景"""
        config = {
            "playwright": {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False,
                "page_timeout": 15000,
                "navigation_timeout": 15000
            },
            "concurrent_limit": 2,
            "max_retries": 2
        }
        
        print("🌍 测试实际应用场景...")
        
        # 爬取实际网站
        results = await stealth_crawl(self.demo_urls["real_world"], config)
        
        successful_count = sum(1 for r in results if r.success)
        
        print(f"✅ 实际应用测试完成:")
        print(f"   测试网站数: {len(results)}")
        print(f"   成功爬取: {successful_count}")
        print(f"   成功率: {(successful_count/len(results)*100):.1f}%")
        
        for i, result in enumerate(results, 1):
            status = "✅" if result.success else "❌"
            print(f"   {i}. {status} {result.url}")
            if result.success:
                print(f"      状态码: {result.status_code}")
                print(f"      内容长度: {len(result.content) if result.content else 0} 字符")
                print(f"      响应时间: {result.response_time:.2f}秒")
                
                # 简单内容分析
                if result.content:
                    content_lower = result.content.lower()
                    if 'quotes' in result.url and 'quote' in content_lower:
                        print(f"      📝 检测到引用内容")
                    elif 'books' in result.url and 'book' in content_lower:
                        print(f"      📚 检测到图书内容")
                    elif 'httpbin' in result.url:
                        print(f"      🔧 API测试响应")
            else:
                print(f"      错误: {result.error}")
                
async def main():
    """主函数"""
    demo = StealthCrawlerDemo()
    await demo.run_demo()
    
if __name__ == "__main__":
    asyncio.run(main())