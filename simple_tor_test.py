#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的Tor状态测试
"""

import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json

async def test_tor_status():
    """测试Tor状态"""
    print("🧅 开始测试Tor状态...")
    
    exit_stack = AsyncExitStack()
    
    try:
        # 连接到服务器
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"],
            env=None
        )
        
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        await session.initialize()
        print("✅ 已连接到MCP服务器")
        
        # 测试Tor引导状态
        print("\n🔄 检查Tor引导状态...")
        result = await session.call_tool("get_tor_bootstrap_status", {})
        if result.content:
            print(f"引导状态: {result.content[0].text}")
        else:
            print("❌ 无法获取引导状态")
        
        # 测试Tor IP
        print("\n🌐 检查Tor IP...")
        result = await session.call_tool("check_tor_ip", {})
        if result.content:
            print(f"IP检查: {result.content[0].text}")
        else:
            print("❌ 无法获取IP信息")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await exit_stack.aclose()
        print("\n🧹 测试完成")

if __name__ == "__main__":
    asyncio.run(test_tor_status())