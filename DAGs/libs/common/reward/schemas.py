# D:\city_chain_project\network\DAGs\common\reward\schemas.py
"""
dataclass / pydantic schemas
"""
from __future__ import annotations
from dataclasses import dataclass
import time


@dataclass
class PoH:
    holder_id: str
    original_tx_id: str
    lat: float
    lon: float
    ttl_sec: int
    accepted_at: float | None = None


@dataclass
class Contribution:
    node_id: str
    score: float
    timestamp: float = time.time()
