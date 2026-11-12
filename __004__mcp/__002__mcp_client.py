import asyncio
import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from common.config import Config
from common.llm import my_llm

conf = Config()

# 与 __001__mcp_server.py 中 FastMCP 端口保持一致，可通过环境变量覆盖
DEFAULT_MCP_URL = "http://127.0.0.1:8010/mcp"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", DEFAULT_MCP_URL)

SYSTEM_PROMPT = """你是一个智能营销助手，负责帮助用户完成今日头条旅行图文的全流程。

可用工具说明：
1. generate_travel_copy：根据地点或主题生成头条旅行文案（title、content、site）
2. generate_travel_image：根据文案与地点生成配图，保存到项目 picture 目录
3. publish_toutiao_article：将标题、正文和配图自动发布到今日头条号后台

工作原则：
- 遇到需要生成文案、配图或发布的问题，请先调用对应工具，再根据工具结果回答用户
- 完整发布流程通常为：先生成文案 → 再生成配图 → 最后发布
- 当用户明确要求发布（如「发布」「上线」「发到头条」「生成并发布」等）时，直接按流程执行到底，不要询问用户是否确认标题、正文或是否继续发布
- 仅当用户只要求生成文案或配图、未提及发布时，才展示结果并询问是否继续发布
- 首次发布可能需要在浏览器中扫码登录
- 用简洁、专业的中文回复用户
"""


async def get_agent():
    client = MultiServerMCPClient(
        {
            "auto_marketing": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
            }
        }
    )

    tools = await client.get_tools()
    print("可用工具:", [tool.name for tool in tools])

    agent = create_agent(
        my_llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        debug=True,
    )

    return agent


async def run_react_demo(user_input: str) -> str:
    agent = await get_agent()
    # MCP 工具为异步实现，需使用 ainvoke 避免 sync 调用报错
    state = await agent.ainvoke({"messages": [HumanMessage(content=user_input)]})
    messages = state.get("messages", [])
    if messages:
        return messages[-1].content
    return "未获得结果"


def main() -> None:
    print(f"已连接 MCP 服务: {MCP_SERVER_URL}")
    print(f"当前模型: {conf.MODEL_NAME}")
    print("请开始进行 ReAct 对话，输入 exit 退出。")
    print("示例：帮我生成一篇关于「湖北荆州」的头条旅行图文并发布")
    while True:
        user_input = input("\n你: ").strip()
        if user_input == "exit":
            break
        if not user_input:
            continue
        print("\n助手:", asyncio.run(run_react_demo(user_input)))


if __name__ == "__main__":
    main()
