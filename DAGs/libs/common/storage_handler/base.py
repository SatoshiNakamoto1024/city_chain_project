# city_chain_project\network\DAGs\common\storage_handler\base.py
"""
共通インターフェース  (インスタンス属性版)
"""
from __future__ import annotations
import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# 100 MB 空き保証
MIN_FREE: Final[int] = 100 * 1024 * 1024


class StorageHandlerBase(ABC):
    """
    root_dir をコンストラクタ引数で受け取り、
    create() で環境変数を評価する仕組みに変更
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    # ---------- helpers ----------
    def _ensure_dir(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _free_bytes(self) -> int:
        self._ensure_dir()
        total, used, free = shutil.disk_usage(self.root_dir)
        return free

    # ---------- public API ----------
    def has_space(self, size: int) -> bool:
        free = self._free_bytes()
        ok = free >= size + MIN_FREE
        if not ok:
            logger.warning(
                "Insufficient space in %s: free=%d required=%d",
                self.root_dir,
                free,
                size + MIN_FREE,
            )
        return ok

    def save_fragment(self, name: str, data: bytes) -> bool:
        if not self.has_space(len(data)):
            return False
        try:
            self._ensure_dir()
            with (self.root_dir / name).open("wb") as fp:
                fp.write(data)
            return True
        except Exception as exc:  # pragma: no cover
            logger.exception("save_fragment error: %s", exc)
            return False

    # ---------- factory ----------
    @classmethod
    @abstractmethod
    def create(cls) -> "StorageHandlerBase":  # pragma: no cover
        """
        サブクラスで環境変数等を読んで root_dir を決定して返す
        """
