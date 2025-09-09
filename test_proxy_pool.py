#!/usr/bin/env python3
"""代理池系统测试脚本

测试代理池的各个组件功能：
- 代理提供者
- 代理验证器
- 代理轮换器
- 代理池管理器
- 增强HTTP客户端
"""

import asyncio
import logging
import time
import json
from typing import List, Dict
from datetime import datetime

# 导入代理池组件
from utils.proxy_pool import ProxyPool, ProxyInfo, ProxyType, ProxyStatus
from utils.proxy_providers import create_proxy_provider
from utils.proxy_validator import create_proxy_validator
from utils.proxy_rotator import create_proxy_rotator
from utils.enhanced_http_client import HttpClientFactory, EnhancedHttpClient
from utils.crawler_framework import CrawlerFramework

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProxyPoolTester:
    """代理池测试器"""
    
    def __init__(self):
        self.test_results = []
        self.test_urls = [
            "http://httpbin.org/ip",
            "https://httpbin.org/user-agent",
            "http://httpbin.org/headers",
            "https://www.google.com",
            "https://www.baidu.com"
        ]
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ 成功" if success else "❌ 失败"
        logger.info(f"{status} - {test_name}: {details}")
    
    async def test_proxy_providers(self):
        """测试代理提供者"""
        logger.info("\n=== 测试代理提供者 ===")
        
        try:
            # 测试免费代理提供者
            free_provider = create_proxy_provider("free")
            free_proxies = await free_provider.fetch_proxies(limit=5)
            
            self.log_test_result(
                "免费代理提供者",
                len(free_proxies) > 0,
                f"获取到 {len(free_proxies)} 个代理"
            )
            
            # 显示代理信息
            for i, proxy in enumerate(free_proxies[:3]):
                logger.info(f"代理 {i+1}: {proxy.host}:{proxy.port} ({proxy.proxy_type.value})")
            
            # 测试本地代理提供者（如果有代理文件）
            try:
                local_provider = create_proxy_provider("local", proxy_file="proxy_list.txt")
                local_proxies = await local_provider.fetch_proxies(limit=3)
                
                self.log_test_result(
                    "本地代理提供者",
                    True,
                    f"尝试从本地文件获取代理，结果: {len(local_proxies)} 个"
                )
            except Exception as e:
                self.log_test_result(
                    "本地代理提供者",
                    False,
                    f"本地代理文件不存在或格式错误: {e}"
                )
            
            return free_proxies
            
        except Exception as e:
            self.log_test_result("代理提供者测试", False, f"异常: {e}")
            return []
    
    async def test_proxy_validator(self, proxies: List[ProxyInfo]):
        """测试代理验证器"""
        logger.info("\n=== 测试代理验证器 ===")
        
        if not proxies:
            self.log_test_result("代理验证器测试", False, "没有可用的代理进行测试")
            return []
        
        try:
            # 创建增强验证器
            validator = create_proxy_validator("enhanced", config={
                "timeout": 10,
                "test_urls": ["http://httpbin.org/ip"],
                "check_anonymity": True
            })
            
            # 验证前几个代理
            test_proxies = proxies[:3]
            valid_proxies = []
            
            for proxy in test_proxies:
                logger.info(f"验证代理: {proxy.host}:{proxy.port}")
                
                is_valid = await validator.validate_proxy(proxy)
                
                if is_valid:
                    valid_proxies.append(proxy)
                    self.log_test_result(
                        f"代理验证 - {proxy.host}:{proxy.port}",
                        True,
                        f"速度: {proxy.response_time:.2f}s, 匿名性: {proxy.anonymity_level}"
                    )
                else:
                    self.log_test_result(
                        f"代理验证 - {proxy.host}:{proxy.port}",
                        False,
                        "代理不可用"
                    )
            
            # 批量验证测试
            logger.info("测试批量验证...")
            batch_results = await validator.validate_batch(test_proxies, max_concurrent=2)
            
            valid_count = sum(1 for result in batch_results if result)
            self.log_test_result(
                "批量代理验证",
                True,
                f"验证 {len(test_proxies)} 个代理，有效: {valid_count} 个"
            )
            
            return valid_proxies
            
        except Exception as e:
            self.log_test_result("代理验证器测试", False, f"异常: {e}")
            return []
    
    async def test_proxy_rotator(self, proxies: List[ProxyInfo]):
        """测试代理轮换器"""
        logger.info("\n=== 测试代理轮换器 ===")
        
        if not proxies:
            self.log_test_result("代理轮换器测试", False, "没有可用的代理进行测试")
            return
        
        try:
            # 测试轮询轮换器
            round_robin_rotator = create_proxy_rotator("round_robin")
            round_robin_rotator.add_proxies(proxies)
            
            logger.info("测试轮询轮换...")
            selected_proxies = []
            for i in range(min(5, len(proxies) * 2)):
                proxy = round_robin_rotator.get_proxy()
                selected_proxies.append(proxy)
                logger.info(f"轮询 {i+1}: {proxy.host}:{proxy.port}")
            
            self.log_test_result(
                "轮询轮换器",
                len(selected_proxies) > 0,
                f"成功轮换 {len(selected_proxies)} 次"
            )
            
            # 测试自适应轮换器
            adaptive_rotator = create_proxy_rotator("adaptive")
            adaptive_rotator.add_proxies(proxies)
            
            logger.info("测试自适应轮换...")
            for i in range(3):
                proxy = adaptive_rotator.get_proxy()
                # 模拟使用记录
                adaptive_rotator.record_usage(proxy, success=True, response_time=0.5 + i * 0.1)
                logger.info(f"自适应 {i+1}: {proxy.host}:{proxy.port}")
            
            self.log_test_result(
                "自适应轮换器",
                True,
                "自适应轮换测试完成"
            )
            
        except Exception as e:
            self.log_test_result("代理轮换器测试", False, f"异常: {e}")
    
    async def test_proxy_pool_manager(self):
        """测试代理池管理器"""
        logger.info("\n=== 测试代理池管理器 ===")
        
        try:
            # 创建代理池组件
            providers = [create_proxy_provider("free")]
            validator = create_proxy_validator("enhanced", config={"timeout": 8})
            rotator = create_proxy_rotator("adaptive")
            
            # 创建代理池管理器
            pool_manager = ProxyPool()
            
            # 刷新代理池
            await pool_manager.refresh_proxies()
            
            # 等待代理池初始化
            await asyncio.sleep(5)
            
            # 获取代理
            proxy = pool_manager.get_proxy()
            
            if proxy:
                self.log_test_result(
                    "代理池管理器 - 获取代理",
                    True,
                    f"获取到代理: {proxy.host}:{proxy.port}"
                )
                
                # 标记代理成功
                pool_manager.mark_proxy_success(proxy, response_time=0.8)
                
                self.log_test_result(
                    "代理池管理器 - 记录使用",
                    True,
                    "成功记录代理使用情况"
                )
            else:
                self.log_test_result(
                    "代理池管理器 - 获取代理",
                    False,
                    "未能获取到可用代理"
                )
            
            # 获取统计信息
            stats = pool_manager.get_stats()
            self.log_test_result(
                "代理池管理器 - 统计信息",
                True,
                f"总代理数: {stats.get('total_proxies', 0)}, 可用: {stats.get('active_proxies', 0)}"
            )
            
            # 代理池测试完成
            pass
            
        except Exception as e:
            self.log_test_result("代理池管理器测试", False, f"异常: {e}")
    
    async def test_enhanced_http_client(self):
        """测试增强HTTP客户端"""
        logger.info("\n=== 测试增强HTTP客户端 ===")
        
        try:
            # 创建配置
            config = {
                "use_proxy_pool": True,
                "use_tor": False,  # 暂时禁用Tor以专注测试代理池
                "max_retries": 2,
                "timeout": 15,
                "use_free_proxies": True,
                "rotation_strategy": "adaptive"
            }
            
            # 创建HTTP客户端
            client = HttpClientFactory.create_proxy_client(config)
            
            # 启动代理池
            async with client.session():
                # 测试GET请求
                test_url = "http://httpbin.org/ip"
                logger.info(f"测试GET请求: {test_url}")
                
                try:
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log_test_result(
                            "增强HTTP客户端 - GET请求",
                            True,
                            f"状态码: {response.status_code}, IP: {data.get('origin', 'unknown')}"
                        )
                    else:
                        self.log_test_result(
                            "增强HTTP客户端 - GET请求",
                            False,
                            f"状态码: {response.status_code}"
                        )
                        
                except Exception as e:
                    self.log_test_result(
                        "增强HTTP客户端 - GET请求",
                        False,
                        f"请求失败: {e}"
                    )
                
                # 测试多个请求（验证轮换）
                logger.info("测试代理轮换...")
                ips = set()
                
                for i in range(3):
                    try:
                        response = await client.get("http://httpbin.org/ip")
                        if response.status_code == 200:
                            data = response.json()
                            ip = data.get('origin', 'unknown')
                            ips.add(ip)
                            logger.info(f"请求 {i+1}: IP = {ip}")
                    except Exception as e:
                        logger.warning(f"请求 {i+1} 失败: {e}")
                    
                    await asyncio.sleep(1)
                
                self.log_test_result(
                    "增强HTTP客户端 - 代理轮换",
                    len(ips) > 0,
                    f"使用了 {len(ips)} 个不同的IP地址"
                )
            
            # 获取统计信息
            stats = client.get_stats()
            self.log_test_result(
                "增强HTTP客户端 - 统计信息",
                True,
                f"总请求: {stats['total_requests']}, 成功: {stats['successful_requests']}, 代理请求: {stats['proxy_requests']}"
            )
            
        except Exception as e:
            self.log_test_result("增强HTTP客户端测试", False, f"异常: {e}")
    
    async def test_crawler_framework_integration(self):
        """测试爬虫框架集成"""
        logger.info("\n=== 测试爬虫框架集成 ===")
        
        try:
            # 创建爬虫框架实例
            crawler_config = {
                "use_proxy_pool": True,
                "use_tor": False,
                "max_retries": 2,
                "timeout": 15
            }
            
            crawler = CrawlerFramework(http_config=crawler_config)
            
            # 测试网页内容获取
            test_url = "http://httpbin.org/html"
            logger.info(f"测试网页内容获取: {test_url}")
            
            try:
                result = crawler.fetch_page_content(test_url)
                
                if "error" not in result:
                    self.log_test_result(
                        "爬虫框架 - 网页内容获取",
                        True,
                        f"标题: {result.get('title', 'N/A')[:50]}, 内容长度: {result.get('content_length', 0)}"
                    )
                else:
                    self.log_test_result(
                        "爬虫框架 - 网页内容获取",
                        False,
                        f"错误: {result['error']}"
                    )
                    
            except Exception as e:
                self.log_test_result(
                    "爬虫框架 - 网页内容获取",
                    False,
                    f"异常: {e}"
                )
            
            # 测试异步批量获取
            test_urls = [
                "http://httpbin.org/html",
                "http://httpbin.org/json",
                "http://httpbin.org/xml"
            ]
            
            logger.info(f"测试异步批量获取 {len(test_urls)} 个URL...")
            
            try:
                results = await crawler.batch_fetch_pages_async(test_urls, max_concurrent=2)
                
                success_count = sum(1 for r in results if "error" not in r)
                self.log_test_result(
                    "爬虫框架 - 异步批量获取",
                    success_count > 0,
                    f"成功获取 {success_count}/{len(test_urls)} 个页面"
                )
                
            except Exception as e:
                self.log_test_result(
                    "爬虫框架 - 异步批量获取",
                    False,
                    f"异常: {e}"
                )
            
            # 获取HTTP客户端统计
            stats = crawler.get_http_client_stats()
            self.log_test_result(
                "爬虫框架 - HTTP统计",
                True,
                f"总请求: {stats.get('total_requests', 0)}, 成功率: {stats.get('success_rate', 0):.2%}"
            )
            
        except Exception as e:
            self.log_test_result("爬虫框架集成测试", False, f"异常: {e}")
    
    def print_test_summary(self):
        """打印测试总结"""
        logger.info("\n" + "="*50)
        logger.info("测试总结")
        logger.info("="*50)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"成功: {successful_tests} ✅")
        logger.info(f"失败: {failed_tests} ❌")
        logger.info(f"成功率: {successful_tests/total_tests:.1%}")
        
        if failed_tests > 0:
            logger.info("\n失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  ❌ {result['test_name']}: {result['details']}")
        
        # 保存测试结果
        with open("proxy_pool_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n详细测试结果已保存到: proxy_pool_test_results.json")

async def main():
    """主测试函数"""
    logger.info("开始代理池系统测试...")
    
    tester = ProxyPoolTester()
    
    # 执行各项测试
    proxies = await tester.test_proxy_providers()
    valid_proxies = await tester.test_proxy_validator(proxies)
    await tester.test_proxy_rotator(valid_proxies)
    await tester.test_proxy_pool_manager()
    await tester.test_enhanced_http_client()
    await tester.test_crawler_framework_integration()
    
    # 打印测试总结
    tester.print_test_summary()

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())