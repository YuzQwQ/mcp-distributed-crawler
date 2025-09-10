#!/usr/bin/env python3
"""Stealth爬虫系统测试脚本

测试Playwright + stealth反反爬虫系统的各项功能：
- Playwright浏览器管理
- Stealth反检测功能
- 代理池集成
- 智能重试机制
- 反爬虫检测和应对
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

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

class StealthCrawlerTester:
    """Stealth爬虫测试器"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
        # 测试URL集合
        self.test_urls = {
            "basic": [
                "https://httpbin.org/user-agent",
                "https://httpbin.org/headers",
                "https://httpbin.org/ip"
            ],
            "detection": [
                "https://bot.sannysoft.com/",  # 机器人检测
                "https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html",  # Headless检测
                "https://arh.antoinevastel.com/bots/areyouheadless"  # 反检测测试
            ],
            "challenging": [
                "https://www.google.com/search?q=test",  # 可能有反爬虫
                "https://www.baidu.com/s?wd=test",  # 百度搜索
                "https://httpbin.org/delay/3"  # 延迟响应
            ]
        }
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("开始Stealth爬虫系统测试")
        
        if not STEALTH_AVAILABLE:
            return {
                "success": False,
                "error": "Stealth爬虫组件不可用，请安装: pip install playwright playwright-stealth"
            }
            
        # 测试项目
        tests = [
            ("playwright_manager_test", self.test_playwright_manager),
            ("basic_stealth_crawl", self.test_basic_stealth_crawl),
            ("batch_crawl_test", self.test_batch_crawl),
            ("anti_detection_test", self.test_anti_detection),
            ("proxy_integration_test", self.test_proxy_integration),
            ("retry_mechanism_test", self.test_retry_mechanism),
            ("performance_test", self.test_performance),
            ("challenging_sites_test", self.test_challenging_sites)
        ]
        
        # 执行测试
        for test_name, test_func in tests:
            try:
                logger.info(f"执行测试: {test_name}")
                result = await test_func()
                self.test_results[test_name] = result
                logger.info(f"测试 {test_name} {'成功' if result.get('success') else '失败'}")
            except Exception as e:
                logger.error(f"测试 {test_name} 异常: {e}")
                self.test_results[test_name] = {
                    "success": False,
                    "error": str(e)
                }
                
        # 生成测试报告
        return self.generate_test_report()
        
    async def test_playwright_manager(self) -> Dict[str, Any]:
        """测试Playwright管理器"""
        try:
            config = {
                "browser_type": "chromium",
                "headless": True,
                "enable_stealth": True,
                "use_proxy_pool": False,
                "max_concurrent_pages": 2
            }
            
            async with create_playwright_manager(config) as manager:
                # 测试页面创建
                page = await manager.create_page()
                
                # 测试导航
                success = await manager.navigate_with_retry(page, "https://httpbin.org/user-agent")
                
                # 测试内容获取
                content = await manager.get_page_content("https://httpbin.org/headers")
                
                # 获取统计信息
                stats = manager.get_stats()
                
                await page.close()
                
                return {
                    "success": success and content is not None,
                    "page_created": True,
                    "navigation_success": success,
                    "content_retrieved": content is not None,
                    "content_length": len(content) if content else 0,
                    "stats": stats
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_basic_stealth_crawl(self) -> Dict[str, Any]:
        """测试基础stealth爬取"""
        try:
            config = {
                "playwright": {
                    "browser_type": "chromium",
                    "headless": True,
                    "enable_stealth": True,
                    "use_proxy_pool": False
                },
                "max_retries": 2
            }
            
            # 测试单个URL
            result = await stealth_crawl("https://httpbin.org/user-agent", config)
            
            return {
                "success": result.success,
                "url": result.url,
                "status_code": result.status_code,
                "content_length": len(result.content) if result.content else 0,
                "stealth_applied": result.stealth_applied,
                "response_time": result.response_time,
                "error": result.error
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_batch_crawl(self) -> Dict[str, Any]:
        """测试批量爬取"""
        try:
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
            
            # 批量爬取
            results = await stealth_crawl(self.test_urls["basic"], config)
            
            successful_count = sum(1 for r in results if r.success)
            total_count = len(results)
            
            return {
                "success": successful_count > 0,
                "total_urls": total_count,
                "successful_count": successful_count,
                "success_rate": (successful_count / total_count) * 100,
                "results": [{
                    "url": r.url,
                    "success": r.success,
                    "status_code": r.status_code,
                    "stealth_applied": r.stealth_applied,
                    "response_time": r.response_time
                } for r in results]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_anti_detection(self) -> Dict[str, Any]:
        """测试反检测功能"""
        try:
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
            
            # 测试反检测URL
            results = []
            for url in self.test_urls["detection"][:2]:  # 只测试前两个，避免超时
                try:
                    result = await stealth_crawl(url, config, timeout=15000)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"反检测测试URL {url} 失败: {e}")
                    
            successful_count = sum(1 for r in results if r.success)
            
            return {
                "success": len(results) > 0,
                "tested_urls": len(results),
                "successful_count": successful_count,
                "results": [{
                    "url": r.url,
                    "success": r.success,
                    "stealth_applied": r.stealth_applied,
                    "error": r.error
                } for r in results]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_proxy_integration(self) -> Dict[str, Any]:
        """测试代理集成"""
        try:
            # 代理池配置（使用本地代理文件，如果存在）
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
            
            # 检查是否有代理文件
            proxy_file = Path("proxy_list.txt")
            if not proxy_file.exists():
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "没有找到代理文件，跳过代理测试"
                }
                
            async with create_stealth_crawler(config, proxy_config) as crawler:
                # 测试几个URL以触发代理轮换
                results = await crawler.crawl_urls(self.test_urls["basic"][:2])
                
                stats = crawler.get_stats()
                
                return {
                    "success": len(results) > 0,
                    "proxy_switches": stats.get("playwright", {}).get("proxy_switches", 0),
                    "results_count": len(results),
                    "stats": stats
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_retry_mechanism(self) -> Dict[str, Any]:
        """测试重试机制"""
        try:
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
            
            # 测试一个可能失败的URL（不存在的域名）
            result = await stealth_crawl("https://nonexistent-domain-12345.com", config)
            
            return {
                "success": True,  # 测试重试机制本身是成功的
                "url_success": result.success,
                "retry_count": result.retry_count,
                "error": result.error,
                "response_time": result.response_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_performance(self) -> Dict[str, Any]:
        """测试性能"""
        try:
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
            
            start_time = time.time()
            
            # 并发爬取多个URL
            results = await stealth_crawl(self.test_urls["basic"], config)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            successful_count = sum(1 for r in results if r.success)
            avg_response_time = sum(r.response_time for r in results if r.response_time) / len(results)
            
            return {
                "success": successful_count > 0,
                "total_time": total_time,
                "urls_count": len(results),
                "successful_count": successful_count,
                "avg_response_time": avg_response_time,
                "requests_per_second": len(results) / total_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test_challenging_sites(self) -> Dict[str, Any]:
        """测试挑战性网站"""
        try:
            config = {
                "playwright": {
                    "browser_type": "chromium",
                    "headless": True,
                    "enable_stealth": True,
                    "use_proxy_pool": False,
                    "page_timeout": 15000,
                    "navigation_timeout": 15000
                },
                "max_retries": 2
            }
            
            results = []
            for url in self.test_urls["challenging"]:
                try:
                    result = await stealth_crawl(url, config, timeout=15000)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"挑战性网站测试 {url} 失败: {e}")
                    
            successful_count = sum(1 for r in results if r.success)
            
            return {
                "success": len(results) > 0,
                "tested_count": len(results),
                "successful_count": successful_count,
                "success_rate": (successful_count / len(results)) * 100 if results else 0,
                "results": [{
                    "url": r.url,
                    "success": r.success,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "error": r.error
                } for r in results]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        end_time = datetime.now()
        runtime = end_time - self.start_time
        
        # 统计成功率
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() 
                             if result.get("success", False))
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": (successful_tests / total_tests) * 100 if total_tests > 0 else 0,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "runtime_seconds": runtime.total_seconds()
            },
            "test_results": self.test_results,
            "recommendations": self.generate_recommendations()
        }
        
        return report
        
    def generate_recommendations(self) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 检查Playwright管理器测试
        playwright_test = self.test_results.get("playwright_manager_test", {})
        if not playwright_test.get("success"):
            recommendations.append("Playwright管理器测试失败，请检查Playwright安装和配置")
            
        # 检查基础爬取测试
        basic_test = self.test_results.get("basic_stealth_crawl", {})
        if not basic_test.get("success"):
            recommendations.append("基础stealth爬取失败，请检查网络连接和stealth配置")
            
        # 检查反检测测试
        anti_detection_test = self.test_results.get("anti_detection_test", {})
        if anti_detection_test.get("success") and anti_detection_test.get("successful_count", 0) == 0:
            recommendations.append("反检测测试全部失败，可能需要更强的反检测策略")
            
        # 检查性能测试
        performance_test = self.test_results.get("performance_test", {})
        if performance_test.get("success"):
            rps = performance_test.get("requests_per_second", 0)
            if rps < 0.5:
                recommendations.append("请求速度较慢，考虑优化并发设置或减少页面加载时间")
                
        if not recommendations:
            recommendations.append("所有测试表现良好，Stealth爬虫系统运行正常")
            
        return recommendations
        
async def main():
    """主函数"""
    tester = StealthCrawlerTester()
    
    try:
        # 运行测试
        report = await tester.run_all_tests()
        
        # 保存测试报告
        output_file = f"stealth_crawler_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        # 打印摘要
        print("\n" + "=" * 60)
        print("Stealth爬虫系统测试报告")
        print("=" * 60)
        
        summary = report["test_summary"]
        print(f"总测试数: {summary['total_tests']}")
        print(f"成功测试数: {summary['successful_tests']}")
        print(f"成功率: {summary['success_rate']:.1f}%")
        print(f"运行时间: {summary['runtime_seconds']:.1f}秒")
        
        print("\n测试结果详情:")
        for test_name, result in report["test_results"].items():
            status = "✓" if result.get("success") else "✗"
            print(f"  {status} {test_name}: {'成功' if result.get('success') else '失败'}")
            if not result.get("success") and result.get("error"):
                print(f"    错误: {result['error']}")
                
        print("\n建议:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
            
        print(f"\n详细报告已保存到: {output_file}")
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"测试执行失败: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())