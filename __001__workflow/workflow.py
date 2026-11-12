import asyncio
import uuid

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, RunnableConfig

from __001__workflow.agent_state import WorkflowAgentState
from __001__workflow.checkpointer import sqlite_manager
from __001__workflow.nodes.__001__text_generate_node import text_generate_node
from __001__workflow.nodes.__002__image_generate_node import image_generate_node
from __001__workflow.nodes.__003__check_text_image_node import check_text_image_node
from __001__workflow.nodes.__004__auto_publish_toutiao_node import auto_publish_toutiao_node
from __001__workflow.nodes.__005__generate_html_node import generate_html_node
from __001__workflow.nodes.__006__baidu_image_download_node import baidu_image_download_node
from __001__workflow.nodes.__007__human_approval_node import human_approval_node
from common.config import Config
from common.output_graph_utils import output_pic_graph
from common.path_utils import get_file_path

_conf = Config()


def _internal_runnable_config(thread_id: str) -> RunnableConfig:
    return RunnableConfig(configurable={"thread_id": thread_id})


def _internal_state_to_response(state: dict, thread_id: str) -> dict:
    interrupted = bool(state.get("__interrupt__"))
    return {
        "thread_id": thread_id,
        "needs_approval": interrupted,
        "is_publish_success": state.get("is_publish_success"),
        "output": state.get("output") or "",
        "toutiao_html": state.get("toutiao_html") or "",
        "toutiao_title": state.get("toutiao_title") or "",
        "is_human_approved": state.get("is_human_approved"),
    }


def build_langgraph(checkpointer) -> CompiledStateGraph:
    graph_builder = StateGraph(WorkflowAgentState)

    graph_builder.add_node(text_generate_node.__name__, text_generate_node)
    graph_builder.add_node(image_generate_node.__name__, image_generate_node)
    graph_builder.add_node(baidu_image_download_node.__name__, baidu_image_download_node)
    graph_builder.add_node(generate_html_node.__name__, generate_html_node)
    graph_builder.add_node(check_text_image_node.__name__, check_text_image_node)
    graph_builder.add_node(human_approval_node.__name__, human_approval_node)
    graph_builder.add_node(auto_publish_toutiao_node.__name__, auto_publish_toutiao_node)

    def route_image_node(state: WorkflowAgentState):
        if state.get("image_source") == "baidu":
            return baidu_image_download_node.__name__
        return image_generate_node.__name__

    def route_after_check(state: WorkflowAgentState):
        if state.get("is_can_publish_toutiao", False):
            return generate_html_node.__name__
        return END

    def route_after_human_approval(state: WorkflowAgentState):
        if state.get("is_human_approved"):
            return auto_publish_toutiao_node.__name__
        return END

    def route_after_html(state: WorkflowAgentState):
        if state.get("require_human_approval"):
            return human_approval_node.__name__
        return auto_publish_toutiao_node.__name__

    graph_builder.add_edge(START, text_generate_node.__name__)
    graph_builder.add_conditional_edges(
        text_generate_node.__name__,
        route_image_node,
        path_map=[baidu_image_download_node.__name__, image_generate_node.__name__],
    )
    graph_builder.add_edge(image_generate_node.__name__, check_text_image_node.__name__)
    graph_builder.add_edge(baidu_image_download_node.__name__, check_text_image_node.__name__)
    graph_builder.add_conditional_edges(
        check_text_image_node.__name__,
        route_after_check,
        path_map=[generate_html_node.__name__, END],
    )
    graph_builder.add_conditional_edges(
        generate_html_node.__name__,
        route_after_html,
        path_map=[human_approval_node.__name__, auto_publish_toutiao_node.__name__],
    )
    graph_builder.add_conditional_edges(
        human_approval_node.__name__,
        route_after_human_approval,
        path_map=[auto_publish_toutiao_node.__name__, END],
    )
    graph_builder.add_edge(auto_publish_toutiao_node.__name__, END)

    return graph_builder.compile(checkpointer=checkpointer)


graph = build_langgraph(sqlite_manager.memory)


def _internal_parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


async def start_workflow(
    user_input: str,
    image_source: str | None = None,
    thread_id: str | None = None,
    require_human_approval: bool = False,
) -> dict:
    """
    启动工作流：生成文案与配图；校验通过后生成预览。

    require_human_approval=True 时在人工审核节点中断，需 resume_workflow；
    False 时校验通过后直接发布。
    """
    tid = thread_id or str(uuid.uuid4())
    config = _internal_runnable_config(tid)
    final_state = await asyncio.to_thread(
        graph.invoke,
        {
            "user_input": user_input,
            "image_source": image_source or _conf.IMAGE_SOURCE or "ai",
            "require_human_approval": require_human_approval,
        },
        config,
    )
    return _internal_state_to_response(final_state, tid)


async def resume_workflow(thread_id: str, approval: str) -> dict:
    """在人工审核中断后恢复工作流；批准则继续头条发布，否则结束。"""
    config = _internal_runnable_config(thread_id)
    final_state = await asyncio.to_thread(graph.invoke, Command(resume=approval), config)
    return _internal_state_to_response(final_state, thread_id)


async def run_workflow(
    user_input: str,
    image_source: str | None = None,
    require_human_approval: bool = False,
) -> dict:
    """兼容旧接口，等同 start_workflow。"""
    return await start_workflow(
        user_input,
        image_source=image_source,
        require_human_approval=require_human_approval,
    )


if __name__ == "__main__":
    output_pic_graph(build_langgraph(checkpointer=None), get_file_path("__001__workflow/graph.jpg"))

    async def _demo():
        print("=== 第一次运行（生成并等待审核）===")
        tid = str(uuid.uuid4())
        result = await start_workflow(
            "湖北荆州",
            thread_id=tid,
            require_human_approval=True,
        )
        print(result)
        if not result.get("needs_approval"):
            return
        decision = input("是否批准发布？输入「批准」或「不批准」：")
        print("\n=== 第二次运行（人工审批后继续）===")
        result2 = await resume_workflow(tid, decision)
        print(result2)

    try:
        asyncio.run(_demo())
    finally:
        sqlite_manager.close()
