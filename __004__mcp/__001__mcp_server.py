import os
import sys

# 允许以脚本方式直接启动（保证项目根在 sys.path 中）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

from __001__workflow.nodes.__001__text_generate_node import generate_toutiao_travel_post
from __001__workflow.nodes.__002__image_generate_node import toutiao_image_generator
from __001__workflow.nodes.__004__auto_publish_toutiao_node import auto_publish_toutiao

mcp = FastMCP("AutoMarketing", host="0.0.0.0", port=8010)


@mcp.tool()
def generate_travel_copy(user_input: str) -> dict:
    """根据用户输入的主题或地点，生成适合今日头条发布的旅行图文文案。

    Args:
        user_input: 旅行主题或地点，例如「湖北荆州」「新疆天山」

    Returns:
        字典，字段：title（标题）、content（正文）、site（从输入中提取的地点关键词）
    """
    title, content, site = generate_toutiao_travel_post(user_input)
    return {"title": title, "content": content, "site": site}


@mcp.tool()
def generate_travel_image(title: str, content: str, site: str) -> dict:
    """根据标题、正文和地点调用百炼生图，并将图片保存到项目 picture 目录。

    Args:
        title: 头条图文标题
        content: 头条图文正文
        site: 地点关键词，用于构建生图提示词

    Returns:
        字典，字段：image_path（本地绝对路径）
    """
    image_path, ok = toutiao_image_generator(title, content, site)
    print("生成图片路径：", image_path, "成功:", ok)
    if not ok:
        return {"error": "图片生成失败，请检查 BAILIAN_API_KEY、账户额度与网络", "image_path": ""}
    return {"image_path": image_path}


@mcp.tool()
async def publish_toutiao_article(
    title: str,
    content: str,
    image_paths: list[str] | None = None,
) -> dict:
    """使用 Playwright 在今日头条号后台自动发布图文（首次使用需在浏览器中扫码登录）。

    Args:
        title: 文章标题（建议 2～30 字）
        content: 文章正文
        image_paths: 配图本地路径列表；支持相对路径（相对项目根）或绝对路径，可为空

    Returns:
        字典，字段：success（是否发布成功）、message（结果说明）
    """
    paths = image_paths or []
    success, message = await auto_publish_toutiao(title, content, paths)
    return {"success": success, "message": message}


if __name__ == "__main__":
    mcp.run("streamable-http")
