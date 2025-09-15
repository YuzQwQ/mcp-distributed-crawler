#!/usr/bin/env python3
"""
简单的人性化访问控制测试
"""
import asyncio
import logging
import time
from distributed.access_controller import AccessController, GentleCrawlerMixin
from distributed.worker_node import BaseCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class TestCrawler(BaseCrawler):
    """测试爬虫类"""
    
    def __init__(self, task_id: str):
        super().__init__(task_id)
        self.access_controller = AccessController()
    
    async def crawl(self, task):
        """测试爬取方法"""
        url = task.get("url", "https://example.com")
        
        # 使用人性化访问控制
        await self.access_controller.wait_before_request(url)
        
        return {
            "url": url,
            "status": "success",
            "timestamp": time.time()
        }

async def main():
    """主测试函数"""
    print("🎯 人性化访问控制测试开始")
    print("=" * 50)
    
    # 测试访问控制器
    controller = AccessController()
    
    print("\n🧪 测试域名提取:")
    test_urls = [
        "https://example.com/page1",
        "https://google.com/search",
        "https://github.com/user/repo"
    ]
    
    for url in test_urls:
        domain = controller._extract_domain(url)
        print(f"  {url} -> {domain}")
    
    print("\n🧪 测试延迟计算:")
    for url in test_urls:
        domain = controller._extract_domain(url)
        delay = controller._calculate_delay(domain, url)
        print(f"  {domain} -> 延迟: {delay:.2f}秒")
    
    print("\n🧪 测试爬虫集成:")
    crawler = TestCrawler("test_task")
    
    test_tasks = [
        {"url": "https://example.com/api1"},
        {"url": "https://google.com/search"},
        {"url": "https://github.com/repo"}
    ]
    
    start_time = time.time()
    for i, task in enumerate(test_tasks):
        task_start = time.time()
        print(f"\n任务 {i+1}: {task['url']}")
        
        result = await crawler.crawl(task)
        elapsed = time.time() - task_start
        
        print(f"  ✅ 完成! 耗时: {elapsed:.2f}秒")
    
    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f}秒")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成!")
    print("\n人性化访问控制已启用:")
    print("  • 智能延迟: 1-3秒随机延迟")
    print("  • 域名感知: 不同域名独立控制")
    print("  • 防过载: 防止对单一域名过度请求")

if __name__ == "__main__":
    asyncio.run(main())