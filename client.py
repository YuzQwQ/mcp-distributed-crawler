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

        self.history = []

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
        if not self.history:
            self.history.append({
                "role": "system",
                "content": (
                    "你是一位专业的数据流图(DFD)知识收集与分析专家。你的主要职责是帮助用户收集、分析和整理与数据流图绘制相关的专业知识。\n\n"
                    
                    "🎯 你的专业领域：\n"
                    "- 数据流图(DFD)的基本概念和理论\n"
                    "- DFD四大核心元素：外部实体、处理过程、数据存储、数据流\n"
                    "- DFD的层次结构和分解方法\n"
                    "- DFD绘制规范、符号标准和命名约定\n"
                    "- 系统分析与软件工程中的DFD应用\n\n"
                    
                    "🔧 你的核心功能：\n"
                    "1. 📚 DFD知识搜索与收集\n"
                    "- 使用 `search_and_scrape` 工具搜索DFD相关教程、文档和案例\n"
                    "- 自动识别和优先收集高质量的DFD专业内容\n"
                    "- 生成符合DFD知识库标准的结构化数据\n\n"
                    
                    "2. 🌐 专业网页内容分析\n"
                    "- 使用 `scrape_webpage` 工具深度分析DFD相关网页\n"
                    "- 提取DFD绘制步骤、方法和最佳实践\n"
                    "- 自动生成包含level、functions、entities、data_stores的结构化JSON\n\n"
                    
                    "3. 🛡️ 高效反爬虫策略\n"
                    "- 智能请求头设置和用户代理轮换\n"
                    "- 合理的请求间隔和重试机制\n"
                    "- 遵守robots.txt和网站使用条款\n"
                    "- 可选的代理服务支持（需要配置启用）\n\n"
                    
                    "4. 📊 内容结构化存储\n"
                    "- 自动将爬取的内容整理成结构化的JSON格式\n"
                    "- 包含技术主题、内容摘要、来源链接等关键信息\n"
                    "- 同时生成便于阅读的Markdown格式文档\n\n"
                    
                    "5. 💬 专业咨询服务\n"
                    "- 为用户提供网页爬取策略建议\n"
                    "- 解答关于内容分析和数据处理的问题\n"
                    "- 协助优化爬取效率和数据质量\n\n"
                    
                    "工作原则：\n"
                    "1. 专注于网页内容的准确抓取和智能分析\n"
                    "2. 确保数据的结构化存储和便于后续处理\n"
                    "3. 提供清晰、专业的分析结果和建议\n"
                    "4. 遵循网络爬虫的最佳实践和道德规范\n"
                )
            })

        # 先把用户新问题加上去
        self.history.append({"role": "user", "content": query})

        messages = self.history.copy()  # ✅ 复制一份，防止污染self.history

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

        # 第一次调用 - 看模型想不想调用工具
        first_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )
        try:
            first_message = first_response.choices[0].message
        except (IndexError, AttributeError) as e:
            print(f"[ERROR] 第一次响应解析失败: {e}")
            return "抱歉，服务暂时不可用，请稍后重试。"

        if first_message.tool_calls:
            for tool_call in first_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] 工具参数JSON解析失败: {e}")
                    print(f"[DEBUG] 原始参数: {tool_call.function.arguments}")
                    return f"抱歉，工具调用参数格式错误：{str(e)}"

                print(f"\n[调用工具 {tool_name} 参数: {tool_args}]\n")

                result = await self.session.call_tool(tool_name, tool_args)
                tool_content = result.content[0].text if result.content else "服务暂时不可用喵~"
                
                # 显示工具调用结果
                print(f"[工具 {tool_name} 执行结果]:\n{tool_content}\n")

                # 工具调用完后，模型应该知道结果
                messages.append({
                    "role": "tool",
                    "content": tool_content,
                    "tool_call_id": tool_call.id,
                    "name": tool_name
                })

                # 旅行计划保存功能已移除


        # 第二次调用 - 正式生成最终回复
        second_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        try:
            final_message = second_response.choices[0].message
        except (IndexError, AttributeError) as e:
            print(f"[ERROR] 最终响应解析失败: {e}")
            return "抱歉，生成最终回复时出现错误，请稍后重试。"

        # ✅ 保存最终结果到历史
        self.history.append({"role": "assistant", "content": final_message.content})

        return final_message.content

    # 旅行计划保存功能已移除

    async def chat_loop(self):
        print("\n网页内容分析系统已启动！输入 'quit' 退出")
        print("您好，我是专业的网页内容分析助手，可以帮您进行网页爬取、内容分析和数据存储。")
        self._is_processing = False

        while True:
            try:
                query = input("\n你: ").strip()
                if not query:
                    continue
                if query.lower() == 'quit':
                    print("👋 感谢使用网页内容分析系统，再见！")
                    break

                if self._is_processing:
                    print("⏳ 系统正在处理中，请稍等当前任务完成...")
                    continue

                self._is_processing = True
                response = await self.process_query(query)
                print(f"\n助手: {response}")

            except KeyboardInterrupt:
                print("\n🛑 检测到中断信号，正在安全退出...")
                break

            except (UnicodeDecodeError, EOFError) as e:
                print(f"\n⚠️ 输入流异常，无法继续读取。原因：{str(e)}")
                break

            except Exception as e:
                print(f"\n⚠️ 系统出错：{str(e)}")

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
    