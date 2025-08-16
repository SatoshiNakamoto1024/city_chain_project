# D:\city_chain_project\network\DAGs\common\observability\metrics.py
"""
observability.metrics  … Prometheus Counter / Histogram を定義
"""
from __future__ import annotations
from prometheus_client import Counter, Histogram, start_http_server
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.config import PROM_BIND

_METRICS_STARTED = False

# ---------------------------- Counters ----------------------------
REQUEST_COUNTER = Counter(
    "poh_requests_total",
    "PoH_REQUEST 発行数",
    ["endpoint", "status"],
)

ACK_COUNTER = Counter(
    "poh_ack_total",
    "PoH_ACK 受信数",
    ["endpoint"],
)

PRESENCE_SUCCESS = Counter(
    "presence_success_total",
    "Presence 呼び出し成功",
)

PRESENCE_ERROR = Counter(
    "presence_error_total",
    "Presence 呼び出し失敗",
)

# ---------------------------- Histograms --------------------------
LATENCY_HIST = Histogram(
    "storage_latency_seconds",
    "Mongo 保存完了レイテンシ",
    buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2, 5),
)

def init_metrics() -> None:
    """Prometheus HTTP エンドポイントを立てる (一度だけ)"""
    global _METRICS_STARTED
    if _METRICS_STARTED:
        return
    host, port = PROM_BIND.split(":")
    start_http_server(int(port), addr=host)
    _METRICS_STARTED = True
