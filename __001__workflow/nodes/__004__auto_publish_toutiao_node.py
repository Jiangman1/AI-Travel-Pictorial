import asyncio

from playwright.async_api import async_playwright

from __001__workflow.agent_state import WorkflowAgentState
import os
from common.path_utils import get_file_path


class ToutiaoUploader:

    def __init__(self, headless=False):
        # 头条号 PC 端「发图文」入口（与后台「创作 → 图文」一致；若平台改版可再替换）
        self.publish_url = "https://mp.toutiao.com/profile_v4/graphic/publish"
        # cookie对用户进行记忆
        self.cookie_path = get_file_path("cookie/toutiao_state.json")
        os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
        self.headless = headless
        # 初始化playwright
        self.playwright = None
        # 初始化浏览器
        self.browser = None
        # 初始化上下文
        self.context = None
        # 初始化页面
        self.page = None

    async def launch(self):
        print("开始启动")
        self.playwright = await async_playwright().start()
        print("启动完成")
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        if os.path.exists(self.cookie_path):
            print("携带信息进入")
            self.context = await self.browser.new_context(storage_state=self.cookie_path)
        else:
            self.context = await self.browser.new_context()
        print("开启新页面")
        self.page = await self.context.new_page()
        print("前往头条号发文页")
        await self.page.goto(self.publish_url, wait_until="domcontentloaded")

    async def close(self):
        await self.wait_seconds(4)
        await self.browser.close()
        await self.playwright.stop()

    async def wait_seconds(self, seconds):
        print(f"等待 {seconds} 秒...")
        await self.page.wait_for_timeout(seconds * 1000)

    async def is_on_login_page(self, timeout_ms: int = 3000) -> bool:  # 异步方法，timeout_ms 为等待元素出现的超时时间（毫秒）
        """
        判断当前是否在头条号登录页。
        依据登录页根节点 article.web-login-union，并校验验证码登录表单是否可见。
        """
        # 定位登录页最外层容器（article.web-login-union）
        login_root = self.page.locator("article.web-login-union")
        # 若页面上不存在该节点，说明不在登录页
        if await login_root.count() == 0:
            return False  # 未找到登录容器，返回 False
        try:
            # 等待登录容器变为可见（最多等待 timeout_ms 毫秒）
            await login_root.first.wait_for(state="visible", timeout=timeout_ms)
        except Exception:
            return False  # 超时或等待失败，视为不在登录页
        # 在登录容器内查找「验证码登录」标题元素
        form_title = login_root.locator(
            ".web-login-union__login__form__title",  # 表单标题的 class 选择器
            has_text="验证码登录",  # 限定文本内容为「验证码登录」
        )
        # 标题可见则确认当前为登录页，否则返回 False
        return await form_title.first.is_visible()

    async def check_is_in_login_page_and_login(self):
        for _ in range(100):
            if await self.is_on_login_page():
                print("当前页面为登录页")
                await self.wait_seconds(10)
            else:
                print("当前页面非登录页")
                break
        return

    async def dismiss_popup_by_random_click(self, wait_seconds: float = 1.5, margin: int = 50):
        """
        进入页面后若存在遮罩弹框，在视口内随机点击一处以关闭弹框。
        """
        await self.wait_seconds(wait_seconds)
        # viewport = self.page.viewport_size
        # if not viewport:
        #     viewport = {"width": 1280, "height": 720}
        # width = viewport["width"]
        # height = viewport["height"]
        # x = random.randint(margin, max(margin, width - margin))
        # y = random.randint(margin, max(margin, height - margin))
        # print(f"随机点击 ({x}, {y}) 以关闭弹框")
        await self.page.mouse.click(10, 10)

    async def fill_title(self, title: str, timeout_ms: int = 10000):
        """
        在发文页标题输入框中逐字输入标题（平台要求 2～30 个字）。
        """
        title = title.strip()
        if not title:
            print("标题为空，跳过填写")
            return
        title_input = self.page.locator(".title-wrapper .editor-title textarea")
        await title_input.wait_for(state="visible", timeout=timeout_ms)
        await title_input.click()
        await title_input.type(title, delay=50)
        print(f"已输入标题: {title}")

    async def fill_content(self, content: str, timeout_ms: int = 10000):
        """
        在发文页正文编辑器（ProseMirror）中逐字输入内容。
        """
        content = content.strip()
        if not content:
            print("正文为空，跳过填写")
            return
        editor = self.page.locator(".syl-editor-wrap .syl-editor .ProseMirror")
        await editor.wait_for(state="visible", timeout=timeout_ms)
        await editor.click()
        await editor.type(content, delay=30)
        print("已输入正文")

    async def click_image_toolbar(self, timeout_ms: int = 10000):
        """
        点击工具栏中的图片按钮，打开图片上传面板。
        """
        image_btn = self.page.locator(
            ".syl-toolbar-tool.image.static button.syl-toolbar-button"
        )
        await image_btn.wait_for(state="visible", timeout=timeout_ms)
        await image_btn.click()
        print("已点击图片按钮")

    async def upload_images(self, image_path_list: list, timeout_ms: int = 60000):
        """
        在图片上传面板中自动完成本地上传并插入正文。

        前置条件：需先调用 click_image_toolbar() 打开上传面板。

        流程：
        1. 校验并解析图片路径（相对路径转为项目根目录绝对路径）
        2. 定位「本地上传」隐藏的 file input，通过 set_input_files 选文件
        3. 等待预览列表中出现对应数量的图片项（上传完成）
        4. 点击「确定」将图片插入编辑器

        Args:
            image_path_list: 图片路径列表，支持相对路径或绝对路径
            timeout_ms: 等待上传与面板元素的超时时间（毫秒），默认 60 秒
        """
        # 无图片时直接返回
        if not image_path_list:
            print("图片列表为空，跳过上传")
            return
        # 收集存在的本地图片绝对路径
        paths = []
        for p in image_path_list:
            abs_path = p if os.path.isabs(p) else get_file_path(p)
            if not os.path.exists(abs_path):
                print(f"图片不存在，已跳过: {abs_path}")
                continue
            paths.append(abs_path)
        if not paths:
            print("无有效图片路径，跳过上传")
            return

        # 定位「本地上传」按钮内的 file input（accept=image/*，支持 multiple）
        file_input = self.page.locator(
            "[data-e2e='image-upload'] .btn-upload-handle input[type='file']"
        )
        await file_input.wait_for(state="attached", timeout=timeout_ms)
        # 一次性传入多张图片，触发页面上传逻辑
        await file_input.set_input_files(paths)
        print(f"已选择 {len(paths)} 张图片，等待上传完成...")

        # 等待预览区出现最后一张图的列表项，表示全部上传完成
        image_items = self.page.locator(".upload-image-panel .image-list li")
        await image_items.nth(len(paths) - 1).wait_for(state="visible", timeout=timeout_ms)

        # 点击底部「确定」按钮，将图片插入正文编辑器
        confirm_btn = self.page.locator("button[data-e2e='imageUploadConfirm-btn']")
        await confirm_btn.wait_for(state="visible", timeout=timeout_ms)
        await confirm_btn.click()
        print("图片上传已确认")

    async def click_preview_and_publish(self, timeout_ms: int = 10000):
        """
        点击底部「预览并发布」按钮。
        """
        await self.wait_seconds(5)
        publish_btn = self.page.locator(
            ".publish-footer button.publish-btn-last"
        )
        await publish_btn.wait_for(state="visible", timeout=timeout_ms)
        await publish_btn.click()
        print("已点击预览并发布")

    async def click_confirm_publish(self, timeout_ms: int = 30000):
        """
        点击底部「确认发布」按钮（需在 click_preview_and_publish 之后调用）。
        """
        await self.wait_seconds(3)
        confirm_btn = self.page.locator(
            ".publish-footer button.publish-btn-last",
            has_text="确认发布",
        )
        await confirm_btn.wait_for(state="visible", timeout=timeout_ms)
        await confirm_btn.click()
        print("已点击确认发布")

    async def save_login_state(self):
        await self.context.storage_state(path=self.cookie_path)


async def auto_publish_toutiao(title, content, image_path_list):
    """返回 (是否成功, 结果说明)。失败时把异常原因带回，便于前端和服务端排查。"""
    uploader = None
    try:
        uploader = ToutiaoUploader()
        await uploader.launch()
        await uploader.wait_seconds(3)
        # 判断是否是登录页面
        await uploader.check_is_in_login_page_and_login()
        await uploader.save_login_state()
        await uploader.dismiss_popup_by_random_click()
        await uploader.fill_title(title)
        await uploader.fill_content(content)
        if image_path_list:
            await uploader.click_image_toolbar()
            await uploader.upload_images(image_path_list)
        await uploader.click_preview_and_publish()
        await uploader.click_confirm_publish()
        await uploader.close()
        return True, "发布头条成功"
    except Exception as e:
        print(f"发布头条失败: {e}")
        if uploader is not None:
            try:
                await uploader.close()
            except Exception as close_err:
                print(f"关闭浏览器失败: {close_err}")
        return False, f"发布头条失败：{e}"


def auto_publish_toutiao_node(state: WorkflowAgentState):
    title = state.get("toutiao_title", "")
    content = state.get("toutiao_content", "")
    image_path_list = state.get("toutiao_image_path_list", [])

    is_success, message = asyncio.run(
        auto_publish_toutiao(title, content, image_path_list)
    )
    state["is_publish_success"] = is_success
    state["output"] = message
    return state


if __name__ == "__main__":
    demo_state = {
        "toutiao_title": "新疆天山",
        "toutiao_content": "新疆天山",
        "toutiao_image_path_list": [
            r"D:\HeiMa\讲课相关\武汉黑马03期资料\大模型课程共享\01-code\wuhan3_auto_marketing_project\picture\20260519160131新疆天山.png"
        ],
    }
    print(auto_publish_toutiao_node(demo_state))