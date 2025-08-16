# D:\city_chain_project\network\DAGs\common\object_processing\config.py
"""
object_processing.config
------------------------
環境変数読み込みを 1 か所に集約
"""
from __future__ import annotations
import os

# シャード数（デフォルト 10）
SHARD_COUNT: int = int(os.getenv("SHARD_COUNT", 10))

# 各シャードワーカーの並列度（デフォルト 2）
WORKER_CONCURRENCY: int = int(os.getenv("SHARD_WORKER_CONCURRENCY", 2))
