# D:\city_chain_project\network\DAGs\common\object_processing\event.py
"""
object_processing.event
-----------------------
イベント／オブジェクトの共通モデル + シャード決定ロジック
"""
from __future__ import annotations
import hashlib
import time
import uuid
from dataclasses import dataclass, field
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from object_processing.config import SHARD_COUNT


@dataclass(slots=True)
class BaseEvent:
    """
    最低限のフィールドだけを持つ汎用イベント
    - event_id: UUID v4 文字列
    - created_at: epoch 秒
    - payload: 任意の dict
    """

    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    # ----------------------------------------------------------
    # シャード ID を決定するハッシュ関数
    # ----------------------------------------------------------
    def shard_id(self) -> int:
        """
        event_id の SHA-256 → 下位 4byte → mod SHARD_COUNT
        """
        h = hashlib.sha256(self.event_id.encode()).digest()
        return int.from_bytes(h[:4], "big") % SHARD_COUNT
