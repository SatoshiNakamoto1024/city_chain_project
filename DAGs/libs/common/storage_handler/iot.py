# city_chain_project\network\DAGs\common\storage_handler\iot.py
"""
IoT デバイス向けストレージハンドラ
"""
from __future__ import annotations
from pathlib import Path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.base import StorageHandlerBase


class IOTStorageHandler(StorageHandlerBase):
    ENV_VAR = "IOT_STORAGE_DIR"
    DEFAULT = "./iot_storage"

    @classmethod
    def create(cls) -> "IOTStorageHandler":
        root = Path(os.getenv(cls.ENV_VAR, cls.DEFAULT))
        return cls(root)
