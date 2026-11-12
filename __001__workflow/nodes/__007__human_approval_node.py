from langgraph.types import interrupt

from __001__workflow.agent_state import WorkflowAgentState


def _internal_is_approved(value) -> bool:
    """将人工输入规范为是否批准发布。"""
    if value is None:
        return False
    text = str(value).strip()
    lower = text.lower()
    if text in ("批准", "通过") or lower in ("approve", "approved", "yes", "true", "1"):
        return True
    if text in ("不批准", "拒绝") or lower in ("reject", "rejected", "no", "false", "0"):
        return False
    return False


def human_approval_node(state: WorkflowAgentState):
    """人工审核：中断工作流，等待 resume 传入审批结果后再继续。"""
    print("等待人工审核文案与配图…")
    approval_input = interrupt(
        {
            "message": "请审核文案与配图，传入「批准」或「不批准」后继续",
            "title": state.get("toutiao_title", ""),
        }
    )
    approved = _internal_is_approved(approval_input)
    state["is_human_approved"] = approved
    if not approved:
        state["is_publish_success"] = False
        state["output"] = "人工审核未通过，已取消发布"
    return state
