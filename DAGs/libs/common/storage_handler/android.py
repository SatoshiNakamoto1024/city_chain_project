# city_chain_project\network\DAGs\common\storage_handler\android.py
"""
Android 向けストレージハンドラ
"""
from __future__ import annotations
from pathlib import Path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.base import StorageHandlerBase


class AndroidStorageHandler(StorageHandlerBase):
    ENV_VAR = "ANDROID_STORAGE_DIR"
    DEFAULT = "./android_storage"

    @classmethod
    def create(cls) -> "AndroidStorageHandler":
        root = Path(os.getenv(cls.ENV_VAR, cls.DEFAULT))
        return cls(root)
