#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站爬取测试脚本
演示如何使用MCP爬虫系统进行网站内容抓取
"""

import asyncio
import sys
from client import MCPClient

async def test_website_crawling():
    """测试网站爬取功能"""
    client = MCPClient()
    
    try:
        # 连接到MCP服务器
        print("🔗 正在连接到MCP服务器...")
        await client.connect_to_server("server.py")
        print("✅ 已成功连接到MCP服务器")
        
        # 测试网站列表
        test_websites = [
            "https://httpbin.org/html",  # 简单的HTML测试页面
            "https://example.com",       # 经典测试网站
            "https://httpbin.org/json",  # JSON响应测试
        ]
        
        print("\n🧪 开始网站爬取测试...")
        
        for i, url in enumerate(test_websites, 1):
            print(f"\n📄 测试 {i}/{len(test_websites)}: {url}")
            print("-" * 60)
            
            # 构造爬取请求
            query = f"请爬取并分析这个网页的内容: {url}"
            
            try:
                # 执行爬取
                response = await client.process_query(query)
                print(f"✅ 爬取成功!")
                print(f"📊 分析结果:\n{response[:500]}..." if len(response) > 500 else f"📊 分析结果:\n{response}")
                
            except Exception as e:
                print(f"❌ 爬取失败: {str(e)}")
            
            # 添加延迟避免过于频繁的请求
            if i < len(test_websites):
                print("⏳ 等待3秒后继续下一个测试...")
                await asyncio.sleep(3)
        
        print("\n🎉 所有测试完成!")
        
        # 测试搜索功能
        print("\n🔍 测试搜索功能...")
        search_query = "请搜索关于Python爬虫的相关信息"
        try:
            search_response = await client.process_query(search_query)
            print(f"✅ 搜索成功!")
            print(f"📊 搜索结果:\n{search_response[:500]}..." if len(search_response) > 500 else f"📊 搜索结果:\n{search_response}")
        except Exception as e:
            print(f"❌ 搜索失败: {str(e)}")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
    
    finally:
        # 清理资源
        await client.cleanup()
        print("\n🧹 资源清理完成")

async def main():
    """主函数"""
    print("🚀 启动网站爬取测试")
    print("=" * 60)
    
    await test_website_crawling()
    
    print("\n" + "=" * 60)
    print("🏁 测试结束")

if __name__ == "__main__":
    asyncio.run(main())