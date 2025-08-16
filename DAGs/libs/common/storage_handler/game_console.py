# city_chain_project\network\DAGs\common\storage_handler\game_console.py
"""
ゲームコンソール向けストレージハンドラ
"""
from __future__ import annotations
from pathlib import Path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.base import StorageHandlerBase


class GameConsoleStorageHandler(StorageHandlerBase):
    ENV_VAR = "GAME_STORAGE_DIR"
    DEFAULT = "./game_storage"

    @classmethod
    def create(cls) -> "GameConsoleStorageHandler":
        root = Path(os.getenv(cls.ENV_VAR, cls.DEFAULT))
        return cls(root)
