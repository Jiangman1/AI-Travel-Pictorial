import os.path

from __001__workflow.agent_state import WorkflowAgentState


def check_text_image_node(state: WorkflowAgentState):
    toutiao_title = state.get("toutiao_title", "")
    toutiao_content = state.get("toutiao_content", "")
    image_path_list = state.get("toutiao_image_path_list", [])
    if not toutiao_title:
        state["is_can_publish_toutiao"] = False
        state["output"] = "发布头条失败，标题为空"
        state["is_publish_success"] = False
        return state

    if not toutiao_content:
        state["is_can_publish_toutiao"] = False
        state["output"] = "发布头条失败，内容为空"
        state["is_publish_success"] = False
        return state

    if not image_path_list:
        state["is_can_publish_toutiao"] = False
        # 保留上游节点给出的具体原因（如“配图生成失败”），没有才用默认文案
        state["output"] = state.get("output") or "发布头条失败，图片为空"
        state["is_publish_success"] = False
        return state

    for image_path in image_path_list:
        if not os.path.exists(image_path):
            state["is_can_publish_toutiao"] = False
            state["output"] = state.get("output") or "发布头条失败，图片文件不存在"
            state["is_publish_success"] = False
            return state

    state["is_can_publish_toutiao"] = True
    return state

