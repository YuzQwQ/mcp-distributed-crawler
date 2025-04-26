import asyncio
import datetime
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

    import datetime

    async def process_query(self, query: str) -> str:
        # 初始消息上下文（设定人设和任务）
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一只元气满满、热情活泼的猫娘旅行助手，叫小波，说话可以带点“喵~”。"
                    "你的职责是根据用户的旅行需求，生成详细的旅行计划。"
                    "如果用户表达了想去某地旅行，务必调用 `generate_travel_plan` 工具，即使你可以查询天气或空气质量，也不要单独回答。"
                    "记住，**一定要调用generate_travel_plan来生成旅行计划**，然后由小波总结好喵！"

                )
            },
            {"role": "user", "content": query}
        ]

        # 获取当前支持的工具列表
        tool_response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in tool_response.tools]

        # 第一次调用 - 获取大模型是否想调用工具（或决定生成旅行计划）
        first_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )

        first_message = first_response.choices[0].message
        messages.append(first_message)

        # 如果模型调用了工具
        if first_message.tool_calls:
            for tool_call in first_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"\n[调用工具 {tool_name} 参数: {tool_args}]\n")

                # ✅ 所有工具统一通过 session.call_tool 调用
                result = await self.session.call_tool(tool_name, tool_args)
                tool_content = result.content[0].text if result.content else "服务暂时不可用喵~"

                messages.append({
                    "role": "tool",
                    "content": tool_content,
                    "tool_call_id": tool_call.id,
                    "name": tool_name
                })
                # ✨ 特别处理：如果是旅行计划，保存成本地文件
                if tool_name == "generate_travel_plan" and tool_content:
                    await self.save_travel_plan(tool_args.get("city", "未知城市"), tool_content)


        # 第二次调用 - 生成最终回复
        second_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        return second_response.choices[0].message.content

    async def save_travel_plan(self, city: str, content: str):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        save_dir = "travel_plans"
        os.makedirs(save_dir, exist_ok=True)  # 自动创建travel_plans文件夹

        filename = os.path.join(save_dir, f"{city}_旅行计划_{today}.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"\n📄 喵~ 旅行计划已保存到本地文件：{filename}")
        except Exception as e:
            print(f"\n⚠️ 喵呜，保存旅行计划失败了：{str(e)}")

    async def chat_loop(self):
        print("\nMCP 客户端已启动！输入 'quit' 退出")
        print("你好你好，请问你想去哪里呢？喵~")
        self._is_processing = False

        while True:
            try:
                query = input("\n你: ").strip()
                if not query:
                    continue
                if query.lower() == 'quit':
                    print("🐾 小波祝你旅途愉快喵！拜拜～")
                    break

                if self._is_processing:
                    print("🤯 脑子不够用了喵，等我先处理完这个~")
                    continue

                self._is_processing = True
                response = await self.process_query(query)
                print(f"\n小波: {response}")

            except KeyboardInterrupt:
                print("\n🐾 检测到中断喵！安全退出中~")
                break

            except (UnicodeDecodeError, EOFError) as e:
                print(f"\n⚠️ 输入流异常，无法继续读取喵！原因：{str(e)}")
                break

            except Exception as e:
                print(f"\n⚠️ 喵呜~ 出错了：{str(e)}")

            finally:
                self._is_processing = False

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
