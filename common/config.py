import os

from dotenv import load_dotenv

from common.path_utils import get_file_path

# 依次尝试：显式指定的 ENV_FILE → 项目根目录 .env → 旧机器的绝对路径（兼容历史环境）
_ENV_CANDIDATES = [
    os.getenv("ENV_FILE"),
    get_file_path(".env"),
    r"D:\my_duyi_project_dir\my_env\wuhan3/.env",
]

for _env_path in _ENV_CANDIDATES:
    if _env_path and os.path.isfile(_env_path):
        load_dotenv(_env_path, override=False)
        break

class Config:
    def __init__(self):
        self.MODEL_API_KEY = os.getenv("MODEL_API_KEY")
        self.MODEL_BASE_URL = os.getenv("MODEL_BASE_URL")
        self.MODEL_NAME = os.getenv("MODEL_NAME")

        self.BAILIAN_API_KEY = os.getenv("BAILIAN_API_KEY")
        # 百炼生图模型，可随时在 .env 里替换（以控制台「模型广场」的模型 ID 为准）
        self.BAILIAN_IMAGE_MODEL = (
            os.getenv("BAILIAN_IMAGE_MODEL") or "qwen-image-2.1-pro"
        ).strip()
        self.BAILIAN_IMAGE_SIZE = (os.getenv("BAILIAN_IMAGE_SIZE") or "2048*2048").strip()

        # 配图来源：ai（百炼生图）| baidu（百度图片下载）
        self.IMAGE_SOURCE = os.getenv("IMAGE_SOURCE", "ai").strip().lower()

        missing = [
            name
            for name in ("MODEL_API_KEY", "MODEL_BASE_URL", "MODEL_NAME")
            if not getattr(self, name)
        ]
        if missing:
            print(
                f"[config] 警告：未读取到 {', '.join(missing)}，"
                f"请在项目根目录创建 .env（可参考 .env.example）"
            )

if __name__ == "__main__":
    config = Config()
    print(config.MODEL_BASE_URL)
    print(config.MODEL_NAME)