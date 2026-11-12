"""
百度图片爬虫工具

【整体流程】
    1. build_baidu_travel_keyword  → 拼搜索词，如「湖北荆州旅行」
    2. search_baidu_image_urls     → 请求百度接口，拿到图片 URL 列表
    3. download_remote_image       → 把单张图片保存到本地
    4. download_baidu_images       → 组合 2 + 3，批量下载

【百度图片搜索接口】
    地址: https://image.baidu.com/search/acjson
    方式: GET，浏览器 F12 网络面板可看到同样请求
    返回: JSON，data 字段里是图片信息列表
"""

import json
import os
import re
import time
import uuid

import requests

BAIDU_IMAGE_SEARCH_URL = "https://image.baidu.com/search/acjson"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Referer": "https://image.baidu.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    # 百度对无 Cookie 的请求经常直接返回空 data，给一个匿名 BAIDUID 能显著提高命中率
    "Cookie": f"BAIDUID={uuid.uuid4().hex.upper()}:FG=1",
}
# 下载图片必须用图片类型的 Accept，复用搜索头会让 CDN 返回错误页
DOWNLOAD_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Referer": "https://image.baidu.com/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
IMAGE_URL_KEYS = ("middleURL", "thumbURL", "hoverURL", "objURL")
_IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF")


def build_baidu_travel_keyword(site: str, fallback: str = "") -> str:
    """构造搜索关键词：地点 +「旅行」。"""
    address = (site or fallback or "").strip()
    if not address:
        return "旅行"
    if address.endswith("旅行"):
        return address
    return f"{address}旅行"


def search_baidu_image_urls(keyword: str, max_count: int = 4) -> list[str]:
    """按关键词搜索，返回图片 URL 列表（含分页与重试）。"""
    if not keyword or max_count <= 0:
        return []

    urls: list[str] = []
    page_start = 0
    page_size = 30

    while len(urls) < max_count and page_start < 90:
        text = _internal_fetch_search_page(keyword, page_start, page_size)
        if text is None:
            break

        items = _internal_parse_search_response(text)
        if not items:
            snippet = (text or "")[:200].replace("\n", " ").replace("\r", " ")
            print(f"百度图片返回里没有可用条目，响应片段: {snippet}")
            break

        for item in items:
            url = _internal_extract_image_url(item)
            if url and url not in urls:
                urls.append(url)
                if len(urls) >= max_count:
                    break

        if len(items) < page_size:
            break
        page_start += page_size

    return urls[:max_count]


def download_remote_image(url: str, save_path: str) -> bool:
    """下载单张图片到本地；校验魔数，失败返回 False。"""
    try:
        abs_path = os.path.abspath(save_path)
        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        resp = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=60)
        resp.raise_for_status()
        content = resp.content
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if not content:
            return False
        # 以 Content-Type 为主，魔数为辅：有些 CDN 返回 AVIF，魔数匹配不到
        if not (content_type.startswith("image/") or content.startswith(_IMAGE_MAGIC)):
            print(f"图片内容不是图片类型: Content-Type={content_type or 'unknown'}, url={url[:80]}")
            return False
        with open(abs_path, "wb") as f:
            f.write(content)
        return True
    except (OSError, requests.RequestException):
        return False


def download_baidu_images(
    keyword: str,
    save_paths: list[str],
    *,
    max_count: int | None = None,
) -> list[str]:
    """
    搜索并批量下载。

    多取候选 URL：某一张下载失败时换下一张，避免搜到 4 条但全失败导致 0 张。
    """
    limit = min(max_count or len(save_paths), len(save_paths), 4)
    if limit <= 0:
        return []

    # 多取候选，下载失败可回退
    candidate_limit = min(max(limit * 5, 20), 60)
    urls = search_baidu_image_urls(keyword, max_count=candidate_limit)
    if not urls:
        print(f"百度图片搜索无可用 URL，keyword={keyword!r}")
        return []

    saved: list[str] = []
    url_idx = 0
    for path in save_paths[:limit]:
        ok = False
        while url_idx < len(urls):
            url = urls[url_idx]
            url_idx += 1
            if download_remote_image(url, path):
                saved.append(path)
                ok = True
                break
        if not ok:
            break

    if len(saved) < limit:
        print(f"百度图片部分下载失败：候选 {len(urls)}，成功 {len(saved)}/{limit}")
    return saved


def _internal_fetch_search_page(keyword: str, page_start: int, page_size: int) -> str | None:
    """请求一页搜索结果，网络抖动时重试。"""
    params = {
        "tn": "resultjson_com",
        "logid": str(int(time.time() * 1000)),
        "ipn": "rj",
        "ct": "201326592",
        "fp": "result",
        "word": keyword,
        "queryWord": keyword,
        "cl": "2",
        "lm": "-1",
        "ie": "utf-8",
        "oe": "utf-8",
        "pn": page_start,
        "rn": page_size,
    }
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(
                BAIDU_IMAGE_SEARCH_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(0.8 * (attempt + 1))
    print(f"百度图片搜索请求失败: {last_err}")
    return None


def _internal_parse_search_response(text: str) -> list[dict]:
    """解析百度 acjson 返回文本为图片信息列表。"""
    text = (text or "").replace("\\'", "'").strip()
    if not text or text == "null":
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'"data"\s*:\s*(\[.*\])\s*[,}]', text, re.S)
        if not match:
            return []
        try:
            payload = {"data": json.loads(match.group(1))}
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict):
        return []
    return [item for item in (payload.get("data") or []) if isinstance(item, dict)]


def _internal_normalize_url(url: str) -> str | None:
    """规范化图片地址：补全协议、仅保留 http(s)。"""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith(("http://", "https://")):
        return url
    return None


def _internal_extract_image_url(item: dict) -> str | None:
    """从单条搜索结果里取出可用图片地址。"""
    for key in IMAGE_URL_KEYS:
        url = _internal_normalize_url(item.get(key) or "")
        if url:
            return url

    replace = item.get("replaceUrl")
    if isinstance(replace, list):
        for entry in replace:
            if not isinstance(entry, dict):
                continue
            for key in ("ObjURL", "ObjUrl", "objURL"):
                url = _internal_normalize_url(entry.get(key) or "")
                if url:
                    return url
    return None
