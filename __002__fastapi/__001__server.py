import os
import sys
from contextlib import asynccontextmanager

# 保证以 `python __002__fastapi/__001__server.py` 方式直接启动时，
# 项目根目录也在 sys.path 中（否则无法 import common / __001__workflow）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from __001__workflow.checkpointer import get_checkpoint_db_path, sqlite_manager
from __001__workflow.workflow import _internal_parse_bool, resume_workflow, start_workflow
from common.config import Config
from common.path_utils import get_file_path

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_BASE_DIR, "static")
_conf = Config()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print(f"LangGraph checkpoint 数据库: {get_checkpoint_db_path()}")
    yield
    sqlite_manager.close()


app = FastAPI(
    title="自动营销助手",
    description="文案生成 · 配图 · 头条发布",
    lifespan=lifespan,
)


@app.get("/")
async def index():
    """打开浏览器访问 http://127.0.0.1:8000 即可进入前端页面。"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/receive_raw_json/")
async def receive_raw_json(data: dict):
    """
    接收 JSON 请求体，字段示例：
    {
      "user_input": "湖北荆州",
      "image_source": "baidu",              # ai | baidu，可选，默认 ai
      "require_human_approval": true        # 可选，默认 false：true 时暂停等待人工审核
    }
    """
    print(f"接收到的数据为:{data}")
    user_input = data.get("user_input", "")
    image_source = data.get("image_source", "ai")
    require_human_approval = _internal_parse_bool(data.get("require_human_approval"), False)
    print(
        f"user_input={user_input!r}, image_source={image_source}, "
        f"require_human_approval={require_human_approval}"
    )
    result = await start_workflow(
        user_input,
        image_source=image_source,
        require_human_approval=require_human_approval,
    )
    return result


@app.post("/approve_workflow/")
async def approve_workflow(data: dict):
    """
    人工审核后恢复工作流并发布。

    请求体示例：
    {
      "thread_id": "uuid-from-start",
      "approval": "批准"   # 或「不批准」
    }
    """
    thread_id = (data.get("thread_id") or "").strip()
    approval = (data.get("approval") or "").strip()
    if not thread_id:
        return {"error": "缺少 thread_id", "needs_approval": False}
    if not approval:
        return {"error": "缺少 approval（批准 / 不批准）", "needs_approval": True, "thread_id": thread_id}
    return await resume_workflow(thread_id, approval)


app.mount("/src", StaticFiles(directory=os.path.join(STATIC_DIR, "src")), name="src")
app.mount("/picture", StaticFiles(directory=get_file_path("picture")), name="picture")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
