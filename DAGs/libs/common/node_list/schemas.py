# D:\city_chain_project\network\DAGs\common\node_list\schemas.py
"""
型定義だけ切り出し
"""
from __future__ import annotations
from typing import TypedDict
from dataclasses import dataclass


class PresenceDoc(TypedDict):
    node_id: str
    last_seen: float          # epoch 秒


@dataclass
class NodeInfo:
    node_id: str
    last_seen: float
