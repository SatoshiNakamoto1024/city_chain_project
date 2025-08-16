# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\metrics.py
"""
poh_metrics.metrics
===================
Prometheus Metric の集中定義と安全取得ユーティリティ。

* register_metrics(registry)
    CollectorRegistry に不足しているメトリクスだけを登録する
    （重複登録による ValueError は発生しない）。

* get_metric(name, registry)
    必要に応じ register_metrics() を呼び、
    該当 Registry に属する Metric オブジェクトを返す。
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary

__all__ = ["register_metrics", "get_metric"]


# --------------------------------------------------------------------------- #
# 内部ヘルパ
# --------------------------------------------------------------------------- #
def _define_metrics(registry: CollectorRegistry) -> None:
    """Registry に未登録のメトリクスだけを定義する。"""
    existing = {m.name for m in registry.collect()}

    # --- PoH issuance --------------------------------------------------------
    if "poh_issued_total" not in existing:
        Counter("poh_issued_total", "Total PoH issued", ["result"], registry=registry)
    if "poh_issue_latency_seconds" not in existing:
        Histogram(
            "poh_issue_latency_seconds",
            "PoH issuance latency (histogram)",
            ["result"],
            registry=registry,
        )
    if "poh_issue_latency_summary_seconds" not in existing:
        Summary(
            "poh_issue_latency_summary_seconds",
            "PoH issuance latency (summary)",
            ["result"],
            registry=registry,
        )

    # --- PoH verification ----------------------------------------------------
    if "poh_verify_latency_seconds" not in existing:
        Histogram(
            "poh_verify_latency_seconds",
            "PoH verification latency (histogram)",
            ["result"],
            registry=registry,
        )
    if "poh_verify_latency_summary_seconds" not in existing:
        Summary(
            "poh_verify_latency_summary_seconds",
            "PoH verification latency (summary)",
            ["result"],
            registry=registry,
        )

    # --- GC / peers ----------------------------------------------------------
    if "gc_events_total" not in existing:
        Counter(
            "gc_events_total",
            "Number of garbage-collection events",
            ["type"],
            registry=registry,
        )
    if "active_peers" not in existing:
        Gauge("active_peers", "Number of currently active peers", registry=registry)

    # --- HTTP / gRPC ---------------------------------------------------------
    if "http_requests_total" not in existing:
        Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status"],
            registry=registry,
        )
    if "grpc_requests_total" not in existing:
        Counter(
            "grpc_requests_total",
            "Total number of gRPC requests",
            ["method", "code"],
            registry=registry,
        )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def register_metrics(registry: CollectorRegistry) -> None:
    """不足しているメトリクスのみを安全に登録する。"""
    _define_metrics(registry)


def get_metric(name: str, registry: CollectorRegistry):
    """
    Metric オブジェクトを返す。存在しなければ自動で定義する。
    """
    if name not in registry._names_to_collectors:          # type: ignore[attr-defined]
        register_metrics(registry)
    return registry._names_to_collectors[name]             # type: ignore[attr-defined]
