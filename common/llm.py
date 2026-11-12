from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from common.config import Config

conf = Config()

# ============ 配置llm区域 ============
my_llm = ChatOpenAI(
    api_key=conf.MODEL_API_KEY,
    base_url=conf.MODEL_BASE_URL,
    model=conf.MODEL_NAME
)

if __name__ == '__main__':
    # 调用模型
    for chunk in my_llm.stream("请介绍一下自己。"):
        print(chunk.content, end="", flush=True)