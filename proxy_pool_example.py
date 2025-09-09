#!/usr/bin/env python3
"""代理池系统使用示例

展示如何在实际项目中使用代理池系统进行网络爬虫和数据采集。
包含多种使用场景和最佳实践。
"""

import asyncio
import logging
import json
from typing import List, Dict
from datetime import datetime

# 导入代理池组件
from utils.enhanced_http_client import HttpClientFactory, get_global_client
from utils.crawler_framework import CrawlerFramework
from utils.proxy_pool import ProxyPool
from utils.proxy_providers import create_proxy_provider
from utils.proxy_validator import create_proxy_validator
from utils.proxy_rotator import create_proxy_rotator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProxyPoolExample:
    """代理池使用示例"""
    
    def __init__(self):
        self.results = []
    
    async def example_1_basic_usage(self):
        """示例1: 基础使用 - 简单的HTTP请求"""
        logger.info("\n=== 示例1: 基础使用 ===")
        
        # 创建简单的代理客户端
        config = {
            "use_proxy_pool": True,
            "use_tor": True,
            "max_retries": 3,
            "timeout": 30
        }
        
        client = HttpClientFactory.create_proxy_client(config)
        
        try:
            # 启动代理池并发送请求
            async with client.session():
                response = await client.get("http://httpbin.org/ip")
                data = response.json()
                
                logger.info(f"请求成功! IP: {data.get('origin')}")
                logger.info(f"状态码: {response.status_code}")
                
                # 获取统计信息
                stats = client.get_stats()
                logger.info(f"客户端统计: {stats}")
                
        except Exception as e:
            logger.error(f"请求失败: {e}")
    
    async def example_2_crawler_integration(self):
        """示例2: 爬虫框架集成 - 网页内容抓取"""
        logger.info("\n=== 示例2: 爬虫框架集成 ===")
        
        # 配置爬虫框架
        crawler_config = {
            "use_proxy_pool": True,
            "use_tor": False,  # 可以根据需要启用
            "max_retries": 2,
            "timeout": 20,
            "use_free_proxies": True,
            "rotation_strategy": "adaptive"
        }
        
        crawler = CrawlerFramework(http_config=crawler_config)
        
        # 目标网站列表
        target_urls = [
            "http://httpbin.org/html",
            "http://httpbin.org/json",
            "https://httpbin.org/user-agent",
            "https://httpbin.org/headers"
        ]
        
        try:
            # 批量异步抓取
            logger.info(f"开始批量抓取 {len(target_urls)} 个页面...")
            
            results = await crawler.batch_fetch_pages_async(
                target_urls, 
                max_concurrent=3
            )
            
            # 处理结果
            successful = 0
            for i, result in enumerate(results):
                if "error" not in result:
                    successful += 1
                    logger.info(f"页面 {i+1}: {result['title'][:50]}... (长度: {result['content_length']})")
                else:
                    logger.warning(f"页面 {i+1} 失败: {result['error']}")
            
            logger.info(f"批量抓取完成: {successful}/{len(target_urls)} 成功")
            
            # 获取HTTP客户端统计
            stats = crawler.get_http_client_stats()
            logger.info(f"爬虫统计: 总请求={stats.get('total_requests')}, 成功率={stats.get('success_rate', 0):.1%}")
            
        except Exception as e:
            logger.error(f"批量抓取失败: {e}")
    
    async def example_3_custom_proxy_pool(self):
        """示例3: 自定义代理池配置"""
        logger.info("\n=== 示例3: 自定义代理池配置 ===")
        
        try:
            # 创建自定义代理提供者
            providers = [
                create_proxy_provider("free"),  # 免费代理
                # 如果有付费代理服务，可以添加:
                # create_proxy_provider("premium", 
                #     service_name="luminati",
                #     api_key="your_api_key",
                #     api_url="your_api_url")
            ]
            
            # 创建自定义验证器
            validator = create_proxy_validator("enhanced", config={
                "timeout": 10,
                "test_urls": ["http://httpbin.org/ip", "https://httpbin.org/get"],
                "check_anonymity": True,
                "max_concurrent": 5
            })
            
            # 创建智能轮换器
            rotator = create_proxy_rotator("smart")
            
            # 创建代理池管理器
            pool_manager = ProxyPool(
                providers=providers,
                validator=validator,
                rotator=rotator,
                config={
                    "min_pool_size": 5,
                    "max_pool_size": 20,
                    "refresh_interval": 600,  # 10分钟刷新
                    "validation_interval": 120,  # 2分钟验证
                    "cleanup_interval": 300,  # 5分钟清理
                    "max_failures": 3
                }
            )
            
            # 启动代理池
            await pool_manager.start()
            logger.info("自定义代理池已启动")
            
            # 等待代理池初始化
            await asyncio.sleep(10)
            
            # 使用代理池
            for i in range(5):
                proxy = await pool_manager.get_proxy()
                if proxy:
                    logger.info(f"获取代理 {i+1}: {proxy.host}:{proxy.port} (类型: {proxy.proxy_type.value})")
                    
                    # 模拟使用代理
                    import random
                    success = random.choice([True, True, False])  # 80%成功率
                    response_time = random.uniform(0.5, 2.0)
                    
                    await pool_manager.record_usage(
                        proxy, 
                        success=success, 
                        response_time=response_time
                    )
                    
                    logger.info(f"代理使用记录: 成功={success}, 响应时间={response_time:.2f}s")
                else:
                    logger.warning(f"第 {i+1} 次未能获取到代理")
                
                await asyncio.sleep(1)
            
            # 获取代理池统计
            stats = pool_manager.get_stats()
            logger.info(f"代理池统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
            
            # 停止代理池
            await pool_manager.stop()
            logger.info("自定义代理池已停止")
            
        except Exception as e:
            logger.error(f"自定义代理池示例失败: {e}")
    
    async def example_4_search_engine_scraping(self):
        """示例4: 搜索引擎数据采集"""
        logger.info("\n=== 示例4: 搜索引擎数据采集 ===")
        
        # 配置高级爬虫
        crawler_config = {
            "use_proxy_pool": True,
            "use_tor": True,
            "max_retries": 3,
            "timeout": 30,
            "use_free_proxies": True,
            "rotation_strategy": "smart",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        }
        
        crawler = CrawlerFramework(http_config=crawler_config)
        
        # 搜索查询列表
        search_queries = [
            "Python web scraping",
            "proxy pool implementation",
            "anti-bot detection"
        ]
        
        try:
            for query in search_queries:
                logger.info(f"搜索查询: {query}")
                
                try:
                    # 使用DuckDuckGo搜索（内置代理支持有限）
                    search_results = crawler.fetch_raw_data(query, engine="duckduckgo", num=5)
                    
                    if search_results and "organic_results" in search_results:
                        results = search_results["organic_results"]
                        logger.info(f"找到 {len(results)} 个搜索结果")
                        
                        # 提取前几个结果的URL
                        urls_to_fetch = [result["link"] for result in results[:3]]
                        
                        # 批量获取页面内容
                        logger.info(f"获取前 {len(urls_to_fetch)} 个页面的详细内容...")
                        
                        page_contents = await crawler.batch_fetch_pages_async(
                            urls_to_fetch,
                            max_concurrent=2
                        )
                        
                        # 分析结果
                        for i, content in enumerate(page_contents):
                            if "error" not in content:
                                logger.info(f"页面 {i+1}: {content['title'][:50]}... (内容长度: {content['content_length']})")
                            else:
                                logger.warning(f"页面 {i+1} 获取失败: {content['error']}")
                    
                    else:
                        logger.warning(f"搜索 '{query}' 未返回结果")
                        
                except Exception as e:
                    logger.error(f"搜索 '{query}' 失败: {e}")
                
                # 间隔时间，避免过于频繁的请求
                await asyncio.sleep(3)
            
            # 最终统计
            stats = crawler.get_http_client_stats()
            logger.info(f"搜索引擎采集统计: {json.dumps(stats, indent=2)}")
            
        except Exception as e:
            logger.error(f"搜索引擎数据采集失败: {e}")
    
    async def example_5_error_handling_and_monitoring(self):
        """示例5: 错误处理和监控"""
        logger.info("\n=== 示例5: 错误处理和监控 ===")
        
        # 配置带监控的客户端
        config = {
            "use_proxy_pool": True,
            "use_tor": True,
            "max_retries": 5,
            "timeout": 15,
            "retry_delay": 2
        }
        
        client = HttpClientFactory.create_proxy_client(config)
        
        # 测试URL列表（包含一些可能失败的URL）
        test_urls = [
            "http://httpbin.org/ip",  # 正常
            "http://httpbin.org/delay/10",  # 延迟
            "http://httpbin.org/status/404",  # 404错误
            "http://httpbin.org/status/500",  # 500错误
            "http://nonexistent-domain-12345.com",  # 域名不存在
            "http://httpbin.org/json",  # 正常
        ]
        
        try:
            async with client.session():
                results = []
                
                for i, url in enumerate(test_urls):
                    logger.info(f"测试URL {i+1}: {url}")
                    
                    start_time = datetime.now()
                    
                    try:
                        response = await client.get(url)
                        
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        result = {
                            "url": url,
                            "status_code": response.status_code,
                            "success": response.status_code < 400,
                            "duration": duration,
                            "error": None
                        }
                        
                        logger.info(f"  ✅ 成功: {response.status_code} ({duration:.2f}s)")
                        
                    except Exception as e:
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        result = {
                            "url": url,
                            "status_code": None,
                            "success": False,
                            "duration": duration,
                            "error": str(e)
                        }
                        
                        logger.error(f"  ❌ 失败: {e} ({duration:.2f}s)")
                    
                    results.append(result)
                    
                    # 短暂延迟
                    await asyncio.sleep(1)
                
                # 统计分析
                total_requests = len(results)
                successful_requests = sum(1 for r in results if r["success"])
                failed_requests = total_requests - successful_requests
                avg_duration = sum(r["duration"] for r in results) / total_requests
                
                logger.info(f"\n错误处理测试结果:")
                logger.info(f"  总请求数: {total_requests}")
                logger.info(f"  成功请求: {successful_requests}")
                logger.info(f"  失败请求: {failed_requests}")
                logger.info(f"  成功率: {successful_requests/total_requests:.1%}")
                logger.info(f"  平均响应时间: {avg_duration:.2f}s")
                
                # 客户端统计
                client_stats = client.get_stats()
                logger.info(f"\n客户端统计:")
                for key, value in client_stats.items():
                    if isinstance(value, (int, float)):
                        logger.info(f"  {key}: {value}")
                
        except Exception as e:
            logger.error(f"错误处理和监控示例失败: {e}")
    
    async def run_all_examples(self):
        """运行所有示例"""
        logger.info("开始运行代理池系统使用示例...")
        
        examples = [
            self.example_1_basic_usage,
            self.example_2_crawler_integration,
            self.example_3_custom_proxy_pool,
            self.example_4_search_engine_scraping,
            self.example_5_error_handling_and_monitoring
        ]
        
        for i, example in enumerate(examples, 1):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"运行示例 {i}: {example.__name__}")
                logger.info(f"{'='*60}")
                
                await example()
                
                logger.info(f"示例 {i} 完成")
                
                # 示例间隔
                if i < len(examples):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"示例 {i} 执行失败: {e}")
        
        logger.info("\n所有示例执行完成!")

async def main():
    """主函数"""
    example = ProxyPoolExample()
    await example.run_all_examples()

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())