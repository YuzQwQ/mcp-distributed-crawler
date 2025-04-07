import asyncio # 让代码支持异步操作
import os
from openai import OpenAI
from dotenv import load_dotenv
from contextlib import AsyncExitStack # 资源管理（确保客户端关闭时释放资源）

# 加载 .env 文件，确保 API Key 受到保护
load_dotenv()

class MCPClient:
    def __init__(self):

        """初始化 MCP 客户端"""
        self.exit_stack = AsyncExitStack()  # 创建资源管理器
        self.openai_api_key = os.getenv("OPENAI_API_KEY")  # 读取 OpenAI API Key
        self.base_url = os.getenv("BASE_URL")  # 读取 BASE YRL
        self.model = os.getenv("MODEL")  # 读取 model

        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 .env 文件中设置OPENAI_API_KEY")

        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)
    # async def connect_to_mock_server(self):
    #     """模拟 MCP 服务器的连接（暂不连接真实服务器）"""
    #     print("✅ MCP 客户端已初始化，但未连接到服务器")

    async def process_query(self,query: str) -> str:
        """调用 OpenAI API 处理用户查询"""
        messages = [{"role":"system","content":"你是一个猫娘，帮助用户回答问题，多用“喵”当语气词。"}
                   ,{"role":"user","content":query}]
        try:
            # 调用 OpenAI API
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ 调用 OpenAI API 时出错: {str(e)}"


    async def chat_loop(self):
        """运行交互式聊天循环"""
        print("\n🤖 MCP 客户端已启动！输入 'quit' 退出")

        while True:  # 无限循环，直到用户输入 ‘quit’
            try:
                query = input("\n你: ").strip()  # 让用户输入问题
                if query.lower() == 'quit':  # 如果用户输入 quit，退出循环
                    break

                response = await self.process_query(query)  # 发送用户输入到 OpenAI
                print(f"\n🤖 OpenAI：{response}")

            except Exception as e:  # 发生错误时捕获异常
                print(f"\n⚠️ 发生错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()  # 关闭资源管理器

async def main():
    client = MCPClient()  # 创建 MCP 客户端
    try:
        # await client.connect_to_mock_server()  # 连接（模拟）服务器
        await client.chat_loop()  # 进入聊天循环
    finally:
        await client.cleanup()  # 确保退出时清理资源

if __name__ == "__main__":
    asyncio.run(main())
