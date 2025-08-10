import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_direct_tool_call():
    # 指定 server 路径（改为你本地 server.py 路径）
    server_script_path = "server.py"
    server_params = StdioServerParameters(command="python", args=[server_script_path])

    async with stdio_client(server_params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            print("✅ 已连接 MCP Server")

            # 查看支持的工具
            tools = await session.list_tools()
            print("📦 可用工具:", [t.name for t in tools.tools])

            # 构造 JSON 请求（测试 query_weather_by_city）
            tool_name = "query_weather_by_city"
            tool_args = {
                "city": "Beijing"
            }

            # 发送请求
            print(f"🚀 调用工具 {tool_name} 参数: {tool_args}")
            result = await session.call_tool(tool_name, tool_args)

            # 输出结果
            print("\n🎯 返回内容:\n", result.content[0].text if result.content else "❌ 没有返回内容")

if __name__ == "__main__":
    asyncio.run(test_direct_tool_call())
