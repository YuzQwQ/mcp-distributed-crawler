#!/usr/bin/env python3
"""
测试人性化访问控制功能
"""
import asyncio
import logging
import time
from distributed.access_controller import AccessController
from distributed.worker_node import StealthCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def test_access_controller():
    """测试访问控制器"""
    print("🧪 测试访问控制器...")
    
    controller = AccessController()
    
    # 测试不同域名的延迟
    test_urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://google.com/search",
        "https://github.com/user/repo",
        "https://example.com/page3",
        "https://stackoverflow.com/questions"
    ]
    
    print("\n测试智能延迟计算:")
    for url in test_urls:
        domain = controller._extract_domain(url)
        delay = controller._calculate_delay_for_domain(domain)
        print(f"  {url} -> 延迟: {delay:.2f}秒")
    
    # 测试速率限制
    print("\n测试速率限制:")
    domain = "example.com"
    
    # 快速连续请求
    for i in range(5):
        allowed = controller._check_rate_limit(domain)
        delay = controller._calculate_delay_for_domain(domain)
        print(f"  请求 {i+1}: {'✓' if allowed else '✗'} 延迟: {delay:.2f}秒")
        
        if i < 4:  # 最后一次不需要等待
            await asyncio.sleep(delay)

async def test_stealth_crawler():
    """测试Stealth爬虫的人性化访问"""
    print("\n🕷️ 测试Stealth爬虫...")
    
    crawler = StealthCrawler("test_task_001")
    
    test_tasks = [
        {"url": "https://example.com/page1"},
        {"url": "https://google.com/search?q=python"},
        {"url": "https://github.com/python/cpython"},
        {"url": "https://example.com/page2"},
    ]
    
    start_time = time.time()
    
    for i, task in enumerate(test_tasks):
        task_start = time.time()
        print(f"\n任务 {i+1}: {task['url']}")
        
        try:
            result = await crawler.crawl(task)
            elapsed = time.time() - task_start
            print(f"  完成! 耗时: {elapsed:.2f}秒")
            print(f"  结果: {result['title']}")
            
        except Exception as e:
            print(f"  错误: {e}")
    
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f}秒")

async def test_concurrent_requests():
    """测试并发请求的延迟控制"""
    print("\n⚡ 测试并发请求控制...")
    
    crawler = StealthCrawler("concurrent_test")
    
    urls = [
        "https://example.com/api1",
        "https://example.com/api2",
        "https://google.com/search1",
        "https://google.com/search2",
        "https://github.com/repo1",
        "https://github.com/repo2",
    ]
    
    tasks = [{"url": url} for url in urls]
    
    start_time = time.time()
    
    # 串行执行以展示延迟效果
    for i, task in enumerate(tasks):
        task_start = time.time()
        print(f"任务 {i+1}: {task['url']}")
        
        try:
            result = await crawler.crawl(task)
            elapsed = time.time() - task_start
            print(f"  完成! 耗时: {elapsed:.2f}秒")
            
        except Exception as e:
            print(f"  错误: {e}")
    
    total_time = time.time() - start_time
    print(f"串行执行 {len(urls)} 个任务")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"平均每个任务耗时: {total_time/len(urls):.2f}秒")

async def main():
    """主测试函数"""
    print("🎯 人性化访问控制测试开始")
    print("=" * 50)
    
    try:
        await test_access_controller()
        await test_stealth_crawler()
        await test_concurrent_requests()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成!")
        print("\n人性化访问控制特性:")
        print("  • 智能延迟计算 (根据域名和访问频率)")
        print("  • 速率限制保护")
        print("  • 防止服务器过载")
        print("  • 模拟人类浏览行为")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())