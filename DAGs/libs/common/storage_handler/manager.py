# city_chain_project\network\DAGs\common\storage_handler\manager.py
"""
StorageManager – device_type 文字列から適切な StorageHandler を返す
"""
from __future__ import annotations
from typing import Type, Mapping, Optional
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.base import StorageHandlerBase
from storage_handler.android import AndroidStorageHandler
from storage_handler.ios import IOSStorageHandler
from storage_handler.iot import IOTStorageHandler
from storage_handler.game_console import GameConsoleStorageHandler

# デバイス種別 → ハンドラクラスのマッピング
_HANDLER_MAP: Mapping[str, Type[StorageHandlerBase]] = {
    "android": AndroidStorageHandler,
    "ios": IOSStorageHandler,
    "ipad": IOSStorageHandler,
    "iot": IOTStorageHandler,
    "game": GameConsoleStorageHandler,
    "console": GameConsoleStorageHandler,
}


class StorageManager:
    """
    デバイスタイプに応じたストレージハンドラを取得するファクトリ
    """

    @staticmethod
    def get_handler(device_type: str) -> Optional[StorageHandlerBase]:
        cls = _HANDLER_MAP.get(device_type.lower())
        if cls is None:
            return None
        return cls.create()
