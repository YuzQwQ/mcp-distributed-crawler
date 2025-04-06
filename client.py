import asyncio # 让代码支持异步操作
from mcp import ClientSession # MCP 客户端会话管理
from contextlib import AsyncExitStack # 资源管理（确保客户端关闭时释放资源）

class MCPClient:
    def __init__(self):
        """初始化 MCP 客户端"""
        self.session = None  # 先不连接 MCP 服务器
        self.exit_stack = AsyncExitStack()  # 创建资源管理器

    async def connect_to_mock_server(self):
        """模拟 MCP 服务器的连接（暂不连接真实服务器）"""
        print("✅ MCP 客户端已初始化，但未连接到服务器")

    async def chat_loop(self):
        """运行交互式聊天循环"""
        print("\nMCP 客户端已启动！输入 'quit' 退出")

        while True:  # 无限循环，直到用户输入 ‘quit’
            try:
                query = input("\nQuery: ").strip()  # 让用户输入问题
                if query.lower() == 'quit':  # 如果用户输入 quit，退出循环
                    break
                print(f"\n🤖 [Mock Response] 你说的是：{query}")  # 返回模拟回复
            except Exception as e:  # 发生错误时捕获异常
                print(f"\n⚠️ 发生错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()  # 关闭资源管理器

async def main():
    client = MCPClient()  # 创建 MCP 客户端
    try:
        await client.connect_to_mock_server()  # 连接（模拟）服务器
        await client.chat_loop()  # 进入聊天循环
    finally:
        await client.cleanup()  # 确保退出时清理资源

if __name__ == "__main__":
    asyncio.run(main())
