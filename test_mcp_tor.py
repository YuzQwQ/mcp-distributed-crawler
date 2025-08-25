#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Tor功能测试脚本
通过MCP客户端测试Tor代理功能
"""

import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json

class MCPTorTester:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.session = None
        self.stdio = None
        self.write = None
    
    async def connect_to_server(self, server_script_path: str):
        """连接到MCP服务器"""
        print(f"🔗 正在连接到服务器: {server_script_path}")
        
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        
        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        
        print(f"✅ 已连接到服务器，可用工具: {[tool.name for tool in tools]}")
        return tools
    
    async def test_tor_proxy(self):
        """测试Tor代理功能"""
        print("\n🧅 开始测试Tor代理功能...")
        
        try:
            # 测试1: 检查IP地址
            print("\n📍 测试1: 检查当前IP地址")
            result = await self.session.call_tool(
                "scrape_webpage",
                {"url": "https://httpbin.org/ip"}
            )
            print(f"IP检查结果: {result.content[0].text if result.content else 'No content'}")
            
            # 测试2: 检查User-Agent
            print("\n🔍 测试2: 检查User-Agent")
            result = await self.session.call_tool(
                "scrape_webpage",
                {"url": "https://httpbin.org/user-agent"}
            )
            print(f"User-Agent结果: {result.content[0].text if result.content else 'No content'}")
            
            # 测试3: 检查HTTP头信息
            print("\n📋 测试3: 检查HTTP头信息")
            result = await self.session.call_tool(
                "scrape_webpage",
                {"url": "https://httpbin.org/headers"}
            )
            print(f"HTTP头信息: {result.content[0].text if result.content else 'No content'}")
            
            # 测试4: 测试Tor检查网站
            print("\n🧅 测试4: 检查是否通过Tor")
            result = await self.session.call_tool(
                "scrape_webpage",
                {"url": "https://check.torproject.org/"}
            )
            print(f"Tor检查结果: {result.content[0].text if result.content else 'No content'}")
            
            # 测试5: 搜索功能测试
            print("\n🔍 测试5: 搜索功能测试")
            result = await self.session.call_tool(
                "search_and_scrape",
                {"keyword": "tor browser test", "top_k": 3}
            )
            print(f"搜索结果: {result.content[0].text[:500] if result.content else 'No content'}...")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
    
    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
    """主函数"""
    print("🧅 MCP Tor功能测试开始")
    print("=" * 50)
    
    tester = MCPTorTester()
    
    try:
        # 连接到服务器
        await tester.connect_to_server("server.py")
        
        # 测试Tor功能
        await tester.test_tor_proxy()
        
        print("\n✅ 所有测试完成")
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()
        print("\n🧹 资源清理完成")

if __name__ == "__main__":
    asyncio.run(main())