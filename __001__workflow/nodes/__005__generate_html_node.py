import base64
import html
import mimetypes
import os

from __001__workflow.agent_state import WorkflowAgentState
from common.path_utils import get_file_path


def _resolve_image_path(image_path: str) -> str:
    return image_path if os.path.isabs(image_path) else get_file_path(image_path)


def _image_to_data_url(image_path: str) -> str | None:
    """将本地图片转为 data URL，便于前端直接展示（无需额外静态服务）。"""
    abs_path = _resolve_image_path(image_path)
    if not os.path.exists(abs_path):
        return None
    mime, _ = mimetypes.guess_type(abs_path)
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    with open(abs_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_preview_html(title: str, content: str, image_path_list: list[str]) -> str:
    """
    根据标题、正文、图片路径生成可在前端直接渲染的完整 HTML 文档。

    Args:
        title: 文章标题
        content: 文章正文（支持换行分段）
        image_path_list: 配图本地路径列表

    Returns:
        完整 HTML 字符串，可直接用于 iframe / Streamlit components.html 等
    """
    # 去除首尾空白并转义 HTML 特殊字符，防止 XSS
    title_text = html.escape(title.strip())
    # 按换行拆分段落，过滤空行
    paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
    # 若无换行但正文非空，整段作为单段落
    if not paragraphs and content.strip():
        paragraphs = [content.strip()]
    # 将每段正文包装为 <p> 标签并拼接
    body_html = "".join(
        f'<p class="article-paragraph">{html.escape(p)}</p>' for p in paragraphs
    )

    # 初始化图片区域 HTML 片段
    images_html = ""
    # 遍历所有配图路径
    for path in image_path_list:
        # 将本地图片转为 base64 data URL
        data_url = _image_to_data_url(path)
        # 转换成功则追加一张图的 <figure> 结构
        if data_url:
            images_html += (
                f'<figure class="article-image">'
                f'<img src="{data_url}" alt="配图" loading="lazy"/>'
                f"</figure>"
            )

    # 初始化标题区域 HTML 片段
    site_html = ""
    # 标题非空时生成 <h1>
    if title_text:
        site_html = f'<h1 class="article-title">{title_text}</h1>'

    # 返回完整 HTML 文档（f-string 中 {{ }} 表示字面量大括号）
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <!-- 指定 UTF-8 编码，正确显示中文 -->
  <meta charset="UTF-8"/>
  <!-- 移动端视口适配 -->
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <!-- 浏览器标签页标题 -->
  <title>{title_text or "头条图文预览"}</title>
  <style>
    /* 全局盒模型与默认边距重置 */
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    /* 页面背景、字体与行高 */
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background: #f5f6f7;
      color: #222;
      line-height: 1.75;
      padding: 24px 16px;
    }}
    /* 文章卡片容器：居中、白底、圆角阴影 */
    .article-card {{
      max-width: 720px;
      margin: 0 auto;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
      overflow: hidden;
    }}
    /* 卡片内边距 */
    .article-body {{
      padding: 24px 20px 32px;
    }}
    /* 主标题样式 */
    .article-title {{
      font-size: 22px;
      font-weight: 600;
      line-height: 1.4;
      margin-bottom: 20px;
      word-break: break-word;
    }}
    /* 图片区块：正文下方留出上间距，内容居中 */
    .article-image {{
      margin: 16px 0 16px;
      text-align: center;
    }}
    /* 配图固定宽度显示（不按百分比缩放） */
    .article-image img {{
      display: block;
      width: 360px;
      height: auto;
      margin: 0 auto;
      border-radius: 8px;
    }}
    /* 正文段落样式 */
    .article-paragraph {{
      font-size: 16px;
      margin-bottom: 14px;
      text-align: justify;
      word-break: break-word;
    }}
    /* 最后一段去掉多余下边距 */
    .article-paragraph:last-child {{
      margin-bottom: 0;
    }}
  </style>
</head>
<body>
  <!-- 语义化文章容器 -->
  <article class="article-card">
    <div class="article-body">
      <!-- 动态插入：标题 HTML -->
      {site_html}
      <!-- 动态插入：正文段落 HTML（正文在上） -->
      {body_html}
      <!-- 动态插入：配图 HTML（图片在下） -->
      {images_html}
    </div>
  </article>
</body>
</html>"""


def generate_html_node(state: WorkflowAgentState):
    title = state.get("toutiao_title", "")
    content = state.get("toutiao_content", "")
    image_path_list = state.get("toutiao_image_path_list", [])

    html_text = build_preview_html(title, content, image_path_list)
    state["toutiao_html"] = html_text
    print("HTML 预览已生成")
    return state


if __name__ == "__main__":
    demo_state = {
        "toutiao_title": "新疆天山：雪峰与草原的秘境之旅",
        "toutiao_content": "天山横亘新疆中部，雪峰、森林与草原交织。\n\n夏季适合徒步与摄影，注意防晒与高反。",
        "toutiao_image_path_list": ["picture/20260519160131新疆天山.png"],
    }
    result = generate_html_node(demo_state)
    output_path = get_file_path("output/toutiao_preview.html")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["toutiao_html"])
    print(f"预览 HTML 已写入: {output_path}")
