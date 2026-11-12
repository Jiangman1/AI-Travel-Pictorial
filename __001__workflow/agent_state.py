from typing import TypedDict, List
from typing_extensions import NotRequired

class WorkflowAgentState(TypedDict):
    # 用户输入
    user_input: str

    # 标题
    toutiao_title: str
    # 内容
    toutiao_content: str
    # 地理位置
    toutiao_site: str
    # 配图来源：ai | baidu
    image_source: str
    #  图片list
    toutiao_image_path_list: List[str]
    # 供前端直接渲染的预览 HTML
    toutiao_html: str
    # 输出的内容
    output: str
    # 发布成功
    is_publish_success: bool
    # 是否可以发布
    is_can_publish_toutiao: bool
    # 是否启用人工审核（由前端/调用方传入）
    require_human_approval: NotRequired[bool]
    # 人工是否批准发布（审核节点 resume 后写入）
    is_human_approved: NotRequired[bool]