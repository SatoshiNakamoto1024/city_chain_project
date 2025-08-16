# D:\city_chain_project\network\DAGs\common\reward\reward_system.py
"""
RewardSystem  … in-memory store + Mongo backend (optional)
"""
from __future__ import annotations
import time
from collections import defaultdict
from typing import Dict
from pymongo import MongoClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from reward.schemas import PoH
from reward.geo import haversine_km
from reward.config import (
    DIST_KM_WEIGHT,
    ONLINE_RATE_WEIGHT,
    TTL_WEIGHT,
    MONGO_URI,
    DB_NAME,
)


class RewardSystem:
    """
    record_contribution / get_score / flush
    Mongo 保存はオプション
    """

    def __init__(self, use_mongo: bool = False):
        self._scores: Dict[str, float] = defaultdict(float)
        self._mongo = MongoClient(MONGO_URI)[DB_NAME] if use_mongo else None

    # --------------------------- public ---------------------------
    def record_contribution(self, node_id: str, score: float) -> None:
        self._scores[node_id] += score
        if self._mongo:
            self._mongo.contributions.insert_one(
                {"node_id": node_id, "score": score, "ts": time.time()}
            )

    def get_score(self, node_id: str) -> float:
        return self._scores.get(node_id, 0.0)

    def all_scores(self) -> dict[str, float]:
        return dict(self._scores)

    def flush(self) -> None:
        self._scores.clear()

    # --------------------------- helpers --------------------------
    def calc_geo_weight(self, poh: PoH, tx_holder_lat: float, tx_holder_lon: float,
                        online_rate: float) -> float:
        """
        地理距離・オンライン率・TTL による weight
        """
        dist_km = haversine_km(poh.lat, poh.lon, tx_holder_lat, tx_holder_lon)
        score = (
            dist_km * DIST_KM_WEIGHT +
            online_rate * ONLINE_RATE_WEIGHT +
            (poh.ttl_sec / 3600) * TTL_WEIGHT
        )
        return score


# -----------------------------------------------------------------
# singleton helper と PoH ACK ハンドラ
# -----------------------------------------------------------------
_reward_sys = RewardSystem()


def on_poh_ack_confirmed(poh: PoH,
                         tx_holder_lat: float,
                         tx_holder_lon: float,
                         online_rate: float = 1.0) -> None:
    """
    保存完了 & accepted 時点で呼ばれる想定
    """
    score = _reward_sys.calc_geo_weight(
        poh, tx_holder_lat, tx_holder_lon, online_rate
    )
    _reward_sys.record_contribution(poh.holder_id, score)
