#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MCP服务器的Tor工具
"""

import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json

class MCPTorToolTester:
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
    
    async def test_tor_tools(self):
        """测试所有Tor相关工具"""
        print("\n🧅 开始测试Tor工具...")
        
        try:
            # 1. 验证Tor配置
            print("\n📋 1. 验证Tor配置")
            result = await self.session.call_tool("validate_tor_config", {})
            print(f"配置验证结果: {result.content[0].text if result.content else 'No content'}")
            
            # 2. 检查Tor引导状态
            print("\n🔄 2. 检查Tor引导状态")
            result = await self.session.call_tool("get_tor_bootstrap_status", {})
            print(f"引导状态: {result.content[0].text if result.content else 'No content'}")
            
            # 3. 检查Tor IP
            print("\n🌐 3. 检查Tor IP")
            result = await self.session.call_tool("check_tor_ip", {})
            print(f"IP检查结果: {result.content[0].text if result.content else 'No content'}")
            
            # 4. 测试Tor连接
            print("\n🔗 4. 测试Tor连接")
            result = await self.session.call_tool("test_tor_connection", {})
            print(f"连接测试结果: {result.content[0].text if result.content else 'No content'}")
            
            # 5. 获取电路信息
            print("\n🔄 5. 获取电路信息")
            result = await self.session.call_tool("get_tor_circuit_info", {})
            print(f"电路信息: {result.content[0].text if result.content else 'No content'}")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
    
    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
    """主函数"""
    print("🧅 MCP Tor工具测试开始")
    print("=" * 50)
    
    tester = MCPTorToolTester()
    
    try:
        # 连接到服务器
        await tester.connect_to_server("server.py")
        
        # 测试Tor工具
        await tester.test_tor_tools()
        
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