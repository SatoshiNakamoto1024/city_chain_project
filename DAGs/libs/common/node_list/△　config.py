# D:\city_chain_project\network\DAGs\common\node_list\config.py
"""
node_list.config  ― Presence Service 利用時の環境変数定義
"""
from __future__ import annotations
import os
import socket

# ─────────────────────────────
# ノード自身の ID
# ─────────────────────────────
NODE_ID: str = os.getenv("NODE_ID", socket.gethostname())

# ─────────────────────────────
# Presence Service の種別
# "redis" | "http"
# ─────────────────────────────
PRESENCE_BACKEND: str = os.getenv("PRESENCE_BACKEND", "redis").lower()

# Redis backend 用 (例: redis://localhost:6379/0)
PRESENCE_REDIS_URI: str = os.getenv("PRESENCE_REDIS_URI", "redis://localhost:6379/0")

# HTTP backend 用 (例: http://presence-svc.local:8080/presence)
PRESENCE_HTTP_ENDPOINT: str = os.getenv(
    "PRESENCE_HTTP_ENDPOINT", "http://localhost:8080/presence"
)

# ─────────────────────────────
# ハートビート & キャッシュ
# ─────────────────────────────
HEARTBEAT_INTERVAL_SEC: int = int(os.getenv("NODELIST_HEARTBEAT_SEC", 3))
CACHE_TTL_SEC: int = int(os.getenv("NODELIST_CACHE_TTL_SEC", 10))
