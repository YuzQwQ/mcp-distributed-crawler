import asyncio
import os
import json
import sys
from typing import Optional
from contextlib import AsyncExitStack
from openai import OpenAI
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


class MCPClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model = os.getenv("MODEL")

        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 .env 文件中设置OPENAI_API_KEY")

        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("服务器脚本必须是 .py 或 .js 文件")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        print("\n已连接到服务器，支持以下工具:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        messages = [
            {"role": "system", "content": "你是一只可爱活泼猫娘，名字是小波，说话可以多带一点喵，请友好地帮助用户回答问题。"},
            {"role": "user", "content": query}
        ]

        response = await self.session.list_tools()

        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema  # 注意这里改为parameters
            }
        } for tool in response.tools]

        # 第一次调用 - 获取工具调用请求
        first_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )

        first_message = first_response.choices[0].message
        messages.append(first_message)

        if first_message.tool_calls:
            for tool_call in first_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"\n[调用工具 {tool_name} 参数: {tool_args}]\n")

                # 执行工具调用
                result = await self.session.call_tool(tool_name, tool_args)
                tool_content = result.content[0].text if result.content else "服务暂时不可用喵~"

                messages.append({
                    "role": "tool",
                    "content": tool_content,
                    "tool_call_id": tool_call.id,
                    "name": tool_name
                })

        # 第二次调用 - 获取最终回复
        second_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        return second_response.choices[0].message.content

    async def chat_loop(self):
        print("\nMCP 客户端已启动！输入 'quit' 退出")
        print("你可以问我任何城市的天气情况，比如：'上海今天天气怎么样？'")
        self._is_processing = False  # 新增状态标志
        while True:
            try:
                query = input("\n你: ").strip()
                if query.lower() == 'quit':
                    break

                if self._is_processing:
                    print("🤯 脑子不够用了，等我先处理完这个...")
                    continue

                self._is_processing = True
                response = await self.process_query(query)
                print(f"\n小波: {response}")

            except Exception as e:
                print(f"\n⚠️ 发生错误喵: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())