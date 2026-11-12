import requests
import streamlit as st
import streamlit.components.v1 as components

DEFAULT_API_BASE = "http://127.0.0.1:8000"
API_PATH = "/receive_raw_json/"
APPROVE_PATH = "/approve_workflow/"


def call_backend(
    api_base: str,
    user_input: str,
    image_source: str = "ai",
    require_human_approval: bool = False,
) -> dict:
    url = f"{api_base.rstrip('/')}{API_PATH}"
    response = requests.post(
        url,
        json={
            "user_input": user_input,
            "image_source": image_source,
            "require_human_approval": require_human_approval,
        },
        timeout=600,
    )
    response.raise_for_status()
    return response.json()


def call_approve(api_base: str, thread_id: str, approval: str) -> dict:
    url = f"{api_base.rstrip('/')}{APPROVE_PATH}"
    response = requests.post(
        url,
        json={"thread_id": thread_id, "approval": approval},
        timeout=600,
    )
    response.raise_for_status()
    return response.json()


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


st.set_page_config(page_title="自动营销 · 头条发布", page_icon="📰", layout="wide")
st.title("自动营销助手")
st.caption("可勾选「发布前人工审核」；不勾选则校验通过后直接发布。")

with st.sidebar:
    api_base = st.text_input("后端地址", value=DEFAULT_API_BASE)
    st.markdown(
        "请先启动 FastAPI：`python __002__fastapi/__001__server.py`"
    )

if "pending_thread_id" not in st.session_state:
    st.session_state.pending_thread_id = None
if "preview_result" not in st.session_state:
    st.session_state.preview_result = None

user_input = st.text_input(
    "请输入营销主题",
    placeholder="例如：湖北荆州、都江堰",
)

image_source = st.radio(
    "配图方式",
    options=["ai", "baidu"],
    format_func=lambda x: "AI 生图（1 张）" if x == "ai" else "百度爬虫（最多 4 张）",
    horizontal=True,
)

require_human_approval = st.checkbox(
    "发布前人工审核",
    value=False,
    help="勾选后先预览再确认发布；不勾选则自动发布到头条。",
)

if st.button("开始处理", type="primary", disabled=not user_input.strip()):
    mode_label = "百度爬虫" if image_source == "baidu" else "AI 生图"
    with st.spinner(f"正在生成文案、使用{mode_label}配图，请稍候…"):
        try:
            result = call_backend(
                api_base,
                user_input.strip(),
                image_source=image_source,
                require_human_approval=require_human_approval,
            )
        except requests.exceptions.ConnectionError:
            st.error(f"无法连接后端，请确认 FastAPI 已启动：{api_base}")
            st.stop()
        except requests.exceptions.HTTPError as e:
            st.error(f"请求失败：HTTP {e.response.status_code}")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("请求超时，工作流可能仍在运行，请稍后重试。")
            st.stop()
        except requests.exceptions.RequestException as e:
            st.error(f"请求异常：{e}")
            st.stop()

    st.session_state.preview_result = result
    if result.get("needs_approval") and result.get("thread_id"):
        st.session_state.pending_thread_id = result["thread_id"]
    else:
        st.session_state.pending_thread_id = None

result = st.session_state.preview_result
pending_tid = st.session_state.pending_thread_id

if result:
    st.divider()
    st.subheader("处理结果")

    needs_approval = bool(result.get("needs_approval") and pending_tid)
    toutiao_html = result.get("toutiao_html") or ""

    if needs_approval:
        st.warning("文案与配图已生成，请预览后确认是否发布到头条。")
    else:
        is_success = as_bool(result.get("is_publish_success"))
        output_msg = result.get("output") or "（无提示信息）"
        if is_success:
            st.success(f"发布成功：{output_msg}")
        else:
            st.error(f"发布未成功：{output_msg}")

    if toutiao_html:
        st.subheader("图文预览")
        components.html(toutiao_html, height=720, scrolling=True)
    elif not needs_approval:
        st.info("未生成 HTML 预览内容，请检查后端日志后重试。")

    if needs_approval:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("批准并发布", type="primary"):
                with st.spinner("正在发布到头条…"):
                    try:
                        final = call_approve(api_base, pending_tid, "批准")
                    except requests.exceptions.RequestException as e:
                        st.error(f"审核请求失败：{e}")
                        st.stop()
                st.session_state.preview_result = final
                st.session_state.pending_thread_id = None
                st.rerun()
        with col2:
            if st.button("拒绝发布"):
                with st.spinner("正在取消发布…"):
                    try:
                        final = call_approve(api_base, pending_tid, "不批准")
                    except requests.exceptions.RequestException as e:
                        st.error(f"审核请求失败：{e}")
                        st.stop()
                st.session_state.preview_result = final
                st.session_state.pending_thread_id = None
                st.rerun()
