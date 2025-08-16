# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\collector.py
"""
poh_metrics.collector
=====================
アプリ／サービス層が直接呼び出す非同期ヘルパ API。
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry

from .metrics import get_metric, register_metrics
from .registry import get_registry


def _resolve_registry(reg: CollectorRegistry | None) -> CollectorRegistry:
    """明示指定が無ければグローバル Registry を使う。"""
    return reg if reg is not None else get_registry()


# --------------------------------------------------------------------------- #
# Public async helpers
# --------------------------------------------------------------------------- #
async def increment_poh(result: str, registry: CollectorRegistry | None = None) -> None:
    reg = _resolve_registry(registry)
    get_metric("poh_issued_total", reg).labels(result=result).inc()


async def observe_issue(
    result: str,
    latency: float,
    registry: CollectorRegistry | None = None,
) -> None:
    reg = _resolve_registry(registry)
    get_metric("poh_issue_latency_seconds", reg).labels(result=result).observe(latency)
    get_metric("poh_issue_latency_summary_seconds", reg).labels(result=result).observe(latency)


async def observe_verify(
    result: str,
    latency: float,
    registry: CollectorRegistry | None = None,
) -> None:
    reg = _resolve_registry(registry)
    get_metric("poh_verify_latency_seconds", reg).labels(result=result).observe(latency)
    get_metric("poh_verify_latency_summary_seconds", reg).labels(result=result).observe(latency)


async def record_gc(
    event_type: str,
    count: int = 1,
    registry: CollectorRegistry | None = None,
) -> None:
    reg = _resolve_registry(registry)
    get_metric("gc_events_total", reg).labels(type=event_type).inc(count)


async def set_active_peers(count: int, registry: CollectorRegistry | None = None) -> None:
    reg = _resolve_registry(registry)
    get_metric("active_peers", reg).set(count)
