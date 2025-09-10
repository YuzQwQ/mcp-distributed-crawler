#!/usr/bin/env python3
"""快速测试Stealth爬虫系统"""

import asyncio
import logging
from utils.stealth_crawler import stealth_crawl

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def quick_test():
    """快速测试"""
    config = {
        "playwright": {
            "browser_type": "chromium",
            "headless": True,
            "enable_stealth": True,
            "use_proxy_pool": False
        },
        "max_retries": 1
    }
    
    print("🚀 快速测试开始")
    
    # 测试单个URL
    result = await stealth_crawl("https://httpbin.org/user-agent", config)
    
    if result.success:
        print(f"✅ 测试成功!")
        print(f"   URL: {result.url}")
        print(f"   状态码: {result.status_code}")
        print(f"   响应时间: {result.response_time:.2f}秒")
        print(f"   Stealth应用: {'是' if result.stealth_applied else '否'}")
        print(f"   内容长度: {len(result.content) if result.content else 0} 字符")
    else:
        print(f"❌ 测试失败: {result.error}")
        
    print("🎉 快速测试结束")

if __name__ == "__main__":
    asyncio.run(quick_test())