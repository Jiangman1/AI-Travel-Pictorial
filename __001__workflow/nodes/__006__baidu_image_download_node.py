"""
工作流节点：百度图片下载

【节点流程】
    读取 state（标题、地点）
        ↓
    构造搜索词 + 本地保存路径
        ↓
    调用 baidu_image_utils 搜索并下载
        ↓
    写回 state["toutiao_image_path_list"]
"""

import datetime

from __001__workflow.agent_state import WorkflowAgentState
from common.baidu_image_utils import build_baidu_travel_keyword, download_baidu_images
from common.path_utils import get_file_path

# 每次最多下载 4 张配图
BAIDU_MAX_IMAGES = 4


def toutiao_baidu_image_downloader(toutiao_title: str, toutiao_site: str) -> list[str]:
    """
    业务入口：根据头条标题和地点，从百度下载配图。

    1. 搜索词 = 地点 + 「旅行」
    2. 预生成 4 个本地路径
    3. 搜索并下载，返回成功的路径列表
    """
    keyword = build_baidu_travel_keyword(toutiao_site, fallback=toutiao_title)
    # 同一批次共用时间戳，避免跨秒导致文件名前缀不一致
    time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    save_paths = [
        get_file_path(f"picture/{time_str}{toutiao_title[:5]}_{i + 1}.png")
        for i in range(BAIDU_MAX_IMAGES)
    ]
    try:
        saved = download_baidu_images(keyword, save_paths, max_count=BAIDU_MAX_IMAGES)
    except Exception as exc:
        print(f"百度图片下载异常: {type(exc).__name__}: {exc}")
        saved = []
    print(f"百度图片搜索关键词: {keyword}，成功下载 {len(saved)} 张")
    return saved


def baidu_image_download_node(state: WorkflowAgentState):
    """LangGraph 节点：从 state 取参数，下载图片后写回 state。"""
    toutiao_title = state.get("toutiao_title", "")
    toutiao_site = state.get("toutiao_site", "")

    image_path_list = toutiao_baidu_image_downloader(toutiao_title, toutiao_site)
    state["toutiao_image_path_list"] = image_path_list

    if image_path_list:
        print(f"百度图片下载成功: {image_path_list}")
    else:
        print("百度图片下载失败，路径列表为空（搜索无结果 / 下载失败 / 网络超时）")
    return state


if __name__ == "__main__":
    # 本地测试：直接运行此文件即可
    print(
        baidu_image_download_node(
            {
                "toutiao_title": "湖北荆州",
                "toutiao_site": "湖北荆州",
            }
        )
    )
