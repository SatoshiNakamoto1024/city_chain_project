# D:\city_chain_project\network\DAGs\common\presence\config.py
"""
common.presence.config
----------------------
Presence Service 用の環境設定

環境変数とデフォルト
====================
NODE_ID                       : ホスト名
PRESENCE_REDIS_URI            : redis://localhost:6379/0
PRESENCE_HTTP_PORT            : 8080
PRESENCE_HEARTBEAT_SEC        : 3          (Heartbeat インターバル)
PRESENCE_RATE_LIMIT_RATE      : 30         (tokens/sec)
PRESENCE_RATE_LIMIT_CAPACITY  : 60         (バースト上限)
"""
from __future__ import annotations
import os
import socket

# ─────────────────────────────────────────
# ノード識別子（PresenceClient でも利用可）
# ─────────────────────────────────────────
NODE_ID: str = os.getenv("NODE_ID", socket.gethostname())

# ─────────────────────────────────────────
# Redis 接続先
# ─────────────────────────────────────────
PRESENCE_REDIS_URI: str = os.getenv(
    "PRESENCE_REDIS_URI",
    "redis://localhost:6379/0",
)

# ─────────────────────────────────────────
# FastAPI サーバー待受ポート
# ─────────────────────────────────────────
PRESENCE_HTTP_PORT: int = int(os.getenv("PRESENCE_HTTP_PORT", 8080))

# ─────────────────────────────────────────
# Heartbeat 間隔（秒）
# ─────────────────────────────────────────
HEARTBEAT_INTERVAL_SEC: int = int(os.getenv("PRESENCE_HEARTBEAT_SEC", 3))

# ─────────────────────────────────────────
# Rate Limiter (サーバー側ミドルウェア用)
# ─────────────────────────────────────────
RATE_LIMIT_RATE: float = float(os.getenv("PRESENCE_RATE_LIMIT_RATE", 30))
RATE_LIMIT_CAPACITY: int = int(os.getenv("PRESENCE_RATE_LIMIT_CAPACITY", 60))

__all__ = [
    "NODE_ID",
    "PRESENCE_REDIS_URI",
    "PRESENCE_HTTP_PORT",
    "HEARTBEAT_INTERVAL_SEC",
    "RATE_LIMIT_RATE",
    "RATE_LIMIT_CAPACITY",
]
