# city_chain_project\network\DAGs\common\storage_handler\ios.py
"""
iOS / iPadOS 向けストレージハンドラ
"""
from __future__ import annotations
from pathlib import Path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.base import StorageHandlerBase


class IOSStorageHandler(StorageHandlerBase):
    ENV_VAR = "IOS_STORAGE_DIR"
    DEFAULT = "./ios_storage"

    @classmethod
    def create(cls) -> "IOSStorageHandler":
        root = Path(os.getenv(cls.ENV_VAR, cls.DEFAULT))
        return cls(root)
