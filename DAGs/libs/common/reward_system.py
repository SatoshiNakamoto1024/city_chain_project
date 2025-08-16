# D:\city_chain_project\network\sending_DAGs\python_sending\common\reward_system.py
"""
reward_system.py
────────────────
ノード貢献度に応じてハーモニートークンを付与する簡易ロジック。

* distribute_once() ── その場で 1 回だけ分配
* auto_distribute() ── バックグラウンドで定期分配 (dev 用)
"""
from __future__ import annotations

import logging
import random
import threading
from typing import Dict
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.node_registry import all_nodes

# ──────────────────────────
# logger
# ──────────────────────────
logger = logging.getLogger("common.reward")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ──────────────────────────
# 定数
# ──────────────────────────
REWARD_RATES = {
    "full": 1.5,
    "light": 1.0,
}
TOKEN_BASE = 10.0  # 1 ステップ当たりの基準トークン

# node_id → 累計報酬
node_rewards: Dict[str, float] = {}

# ──────────────────────────
# 内部 util
# ──────────────────────────
def _calc(node_type: str, score: float) -> float:
    return score * REWARD_RATES.get(node_type, 1.0) * TOKEN_BASE


def _grant(node_id: str, score: float) -> None:
    node = next((n for n in all_nodes if n["node_id"] == node_id), None)
    if node is None:
        logger.warning("unknown node_id=%s", node_id)
        return
    r = _calc(node["node_type"], score)
    node_rewards[node_id] = node_rewards.get(node_id, 0.0) + r
    logger.info("node=%s +%.2f → total=%.2f", node_id, r, node_rewards[node_id])

# ──────────────────────────
# 外部 API
# ──────────────────────────
def distribute_once() -> None:
    """全ノードに対しランダムスコアを付けて 1 回だけ分配"""
    for n in all_nodes:
        _grant(n["node_id"], random.uniform(0.1, 1.0))


def auto_distribute(interval_sec: float = 60.0) -> None:
    """interval_sec ごとに永続的に分配 (dev/debug 用)"""
    distribute_once()
    threading.Timer(interval_sec, auto_distribute, [interval_sec]).start()


# デバッグ起動用
if __name__ == "__main__":  # pragma: no cover
    distribute_once()
