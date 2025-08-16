# D:\city_chain_project\network\DAGs\common\reward\config.py
"""
reward.config  … 環境値 & 定数
"""
from __future__ import annotations
import os

# スコア係数
DIST_KM_WEIGHT: float = float(os.getenv("REWARD_DIST_KM_WEIGHT", 1.0))
ONLINE_RATE_WEIGHT: float = float(os.getenv("REWARD_ONLINE_WEIGHT", 2.0))
TTL_WEIGHT: float = float(os.getenv("REWARD_TTL_WEIGHT", 0.5))

# MongoDB (保存先 / 実プロダクション用)
MONGO_URI: str = os.getenv("REWARD_MONGO_URI", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("REWARD_DB", "reward_db")
