import requests

BASE_URL = "http://127.0.0.1:8000"


def test_receive_raw_json(user_input: str = "都江堰", image_source: str = "ai"):
    url = f"{BASE_URL}/receive_raw_json/"
    payload = {"user_input": user_input, "image_source": image_source}

    print(f"请求 URL: {url}")
    print(f"请求 JSON: {payload}")

    response = requests.post(url, json=payload)
    # raise_for_status()：若 HTTP 状态码为 4xx/5xx（如 404、500），则抛出 requests.HTTPError；
    # 若为 2xx（如 200），则什么都不做，便于在失败时立刻中断，避免继续解析错误响应体
    response.raise_for_status()

    result = response.json()
    print(f"状态码: {response.status_code}")
    # print(f"响应 JSON: {result}")
    return result


if __name__ == "__main__":
    result = test_receive_raw_json()
    print(result["toutiao_html"][:100])
    print(result["is_publish_success"])
    print(result["output"])
