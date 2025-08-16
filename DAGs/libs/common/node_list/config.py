"""
node_list.config  ― 環境変数を１か所にまとめる
"""
from __future__ import annotations
import os
import socket

# ────────────────────────────
# ノード自身の識別子
# ────────────────────────────
NODE_ID: str = os.getenv("NODE_ID", socket.gethostname())

# ────────────────────────────
# Presence backend 選択: "redis" or "http"
# ────────────────────────────
PRESENCE_BACKEND: str = os.getenv("PRESENCE_BACKEND", "redis").lower()

# Redis 用 URI
PRESENCE_REDIS_URI: str = os.getenv("PRESENCE_REDIS_URI", "redis://localhost:6379/0")

# HTTP 用エンドポイント
PRESENCE_HTTP_ENDPOINT: str = os.getenv(
    "PRESENCE_HTTP_ENDPOINT",
    "http://localhost:8080/presence",
)

# ────────────────────────────
# ハートビート & TTL
# ────────────────────────────
HEARTBEAT_INTERVAL_SEC: int = int(os.getenv("NODELIST_HEARTBEAT_SEC", 3))
CACHE_TTL_SEC: int = int(os.getenv("NODELIST_CACHE_TTL_SEC", 10))

# ────────────────────────────
# Presence HTTP サーバ起動ポート
# （app_node_list.py が参照）
# ────────────────────────────
PRESENCE_HTTP_PORT: int = int(os.getenv("PRESENCE_HTTP_PORT", 8080))
