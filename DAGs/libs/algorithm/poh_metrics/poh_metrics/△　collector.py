# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\collector.py
"""
poh_metrics.collector
=====================
アプリ／サービス層が直接呼ぶハイレベル非同期 API。
"""

from __future__ import annotations
from prometheus_client import CollectorRegistry
from .metrics import get_metric

async def increment_poh(result: str, reg: CollectorRegistry) -> None:
    """
    PoH 発行結果をインクリメントします。
    result: "success" | "failure" | "timeout" 等
    """
    metric = get_metric("poh_issued_total", reg)
    metric.labels(result=result).inc()

async def observe_issue(result: str, latency: float, reg: CollectorRegistry) -> None:
    """
    PoH 発行レイテンシを記録（Histogram + Summary）。
    """
    get_metric("poh_issue_latency_seconds", reg).labels(result=result).observe(latency)
    get_metric("poh_issue_latency_summary_seconds", reg).labels(result=result).observe(latency)

async def observe_verify(result: str, latency: float, reg: CollectorRegistry) -> None:
    """
    PoH 検証レイテンシを記録（Histogram + Summary）。
    """
    get_metric("poh_verify_latency_seconds", reg).labels(result=result).observe(latency)
    get_metric("poh_verify_latency_summary_seconds", reg).labels(result=result).observe(latency)

async def record_gc(event_type: str, count: int, reg: CollectorRegistry) -> None:
    """
    Garbage-collection イベントをカウント。
    event_type: "minor" | "major"
    """
    get_metric("gc_events_total", reg).labels(type=event_type).inc(count)

async def set_active_peers(count: int, reg: CollectorRegistry) -> None:
    """
    アクティブピア数を更新します。
    """
    get_metric("active_peers", reg).set(count)
