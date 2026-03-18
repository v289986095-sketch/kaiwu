"""云端同步 — stub 模块

云端功能（账号注册、登录、同步、社区贡献）暂未开放。
所有方法均抛出 CloudSyncError 提示用户。

此文件确保 cli.py 和 recorder.py 中的 import 不会报 ModuleNotFoundError。
"""

from pathlib import Path

from kaiwu.config import KAIWU_HOME

# 本地 token 缓存路径（供 cli.py logout 等引用）
TOKEN_PATH = KAIWU_HOME / "token.json"


class CloudSyncError(Exception):
    """云端同步异常"""
    pass


class CloudSync:
    """云端同步客户端 — stub 版本，所有操作均提示功能暂未开放"""

    _NOT_AVAILABLE = "云端功能暂未开放，敬请期待"

    @property
    def is_logged_in(self) -> bool:
        return False

    def register(self, username: str, password: str, **kwargs) -> dict:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def login(self, username: str, password: str) -> dict:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def verify_email(self, email: str, code: str) -> None:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def forgot_password(self, email: str) -> None:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def reset_password(self, email: str, code: str, new_password: str) -> None:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def sync_all(self) -> dict:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def contribute(self, data: dict) -> bool:
        raise CloudSyncError(self._NOT_AVAILABLE)

    def logout(self) -> None:
        raise CloudSyncError(self._NOT_AVAILABLE)
