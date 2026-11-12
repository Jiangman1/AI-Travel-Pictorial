"""LangGraph checkpoint 持久化（同步 SqliteSaver，磁盘 SQLite）。"""

import os

from langgraph.checkpoint.sqlite import SqliteSaver

from common.path_utils import get_file_path


def get_checkpoint_db_path() -> str:
    return get_file_path("data/langgraph_checkpoints.db")


class SqliteManager:
    def __init__(self, db_path: str | None = None):
        print("初始化 SqliteManager")
        self.db_path = db_path or get_checkpoint_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.memory_ctx = SqliteSaver.from_conn_string(self.db_path)
        self.memory = self.memory_ctx.__enter__()
        self.memory.setup()

    def close(self):
        print("关闭 SqliteManager")
        if self.memory_ctx is not None:
            self.memory_ctx.__exit__(None, None, None)
            self.memory_ctx = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


sqlite_manager = SqliteManager()
