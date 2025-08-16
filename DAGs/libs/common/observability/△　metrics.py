# network/DAGs/common/observability/metrics.py

import time
from prometheus_client import Counter, Histogram
from .exporters import start_metrics_server

# 起動時に metrics エンドポイントを立てる
start_metrics_server()

# PoH_REQUEST 発行数
POH_REQUEST_COUNTER = Counter(
    "poh_request_total",
    "Number of PoH_REQUEST messages issued",
    ["region"]
)

# PoH_ACK 受信数
POH_ACK_COUNTER = Counter(
    "poh_ack_total",
    "Number of PoH_ACK messages received",
    ["region"]
)

# 保存完了レイテンシ分布
STORAGE_LATENCY = Histogram(
    "storage_completion_latency_seconds",
    "Latency from PoH aggregation to storage completion",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2]
)

# Presence 呼び出し成功率
PRESENCE_SUCCESS = Counter(
    "presence_call_success_total",
    "Number of successful Presence Service calls",
    ["region"]
)
PRESENCE_FAILURE = Counter(
    "presence_call_failure_total",
    "Number of failed Presence Service calls",
    ["region"]
)


def record_poh_request(region: str):
    POH_REQUEST_COUNTER.labels(region=region).inc()


def record_poh_ack(region: str):
    POH_ACK_COUNTER.labels(region=region).inc()


def record_storage_latency(elapsed: float):
    STORAGE_LATENCY.observe(elapsed)


def record_presence(success: bool, region: str):
    (PRESENCE_SUCCESS if success else PRESENCE_FAILURE).labels(region=region).inc()
