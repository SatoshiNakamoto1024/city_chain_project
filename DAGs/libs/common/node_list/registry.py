# D:\city_chain_project\network\DAGs\common\node_list\registry.py
"""
node_list.registry  ― アプリインスタンス内のキャッシュ実装
"""
from __future__ import annotations
import asyncio
import time
from typing import List, Dict

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from node_list.schemas import NodeInfo
from node_list.config import CACHE_TTL_SEC

class NodeRegistry:
    """
    - asyncio.Lock でスレッド & async 並列安全
    - get_nodes() は TTL が切れたら空リストを返す（≒再フェッチ要求）
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._nodes: Dict[str, NodeInfo] = {}
        self._expiry = 0.0  # epoch

    # --------------------------------------------------------------
    # public API
    # --------------------------------------------------------------
    async def update(self, nodes: List[NodeInfo]) -> None:
        async with self._lock:
            self._nodes = {n.node_id: n for n in nodes}
            self._expiry = time.time() + CACHE_TTL_SEC

    async def get_nodes(self) -> List[NodeInfo]:
        async with self._lock:
            if time.time() >= self._expiry:
                # TTL 切れ
                return []
            return list(self._nodes.values())

# シングルトン用ファクトリ
_registry_singleton: NodeRegistry | None = None

def get_registry() -> NodeRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = NodeRegistry()
    return _registry_singleton
