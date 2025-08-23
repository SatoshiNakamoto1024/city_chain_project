# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\metrics.py
# poh_metrics/metrics.py
"""
Prometheus Metric 定義 + 安全取得ユーティリティ
"""

from __future__ import annotations

import weakref
from typing import Dict, List

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary

__all__ = ["get_metric", "register_metrics"]

# --------------------------------------------------------------------------- #
# Registry ↔ Metric マッピング（弱参照でリーク防止）
# --------------------------------------------------------------------------- #
_REGISTERED: "weakref.WeakKeyDictionary[CollectorRegistry, Dict[str, object]]"
_REGISTERED = weakref.WeakKeyDictionary()   # {registry: {alias_name: metric}}


# --------------------------------------------------------------------------- #
# 内部ヘルパ
# --------------------------------------------------------------------------- #
def _alias_counter_names(metric_name: str) -> List[str]:
    """
    Counter を family 名（*_total）でも引けるよう
    エイリアス名のリストを返す。
    """
    return [metric_name, f"{metric_name}_total"]


def _map(reg: CollectorRegistry, prom_name: str, metric) -> None:
    """REGISTERED にオブジェクトを登録。Counter は *_total の alias も登録。"""
    targets = (
        _alias_counter_names(prom_name)
        if isinstance(metric, Counter)
        else [prom_name]
    )
    store = _REGISTERED.setdefault(reg, {})
    for t in targets:
        store[t] = metric


def _ensure_counter(
    reg: CollectorRegistry,
    prom_name: str,
    doc: str,
    labels: List[str],
) -> None:
    if prom_name not in reg._names_to_collectors:          # type: ignore[attr-defined]
        Counter(prom_name, doc, labels, registry=reg)
    _map(reg, prom_name, reg._names_to_collectors[prom_name])      # type: ignore[attr-defined]


def _ensure_histogram(
    reg: CollectorRegistry,
    prom_name: str,
    doc: str,
    labels: List[str],
) -> None:
    if prom_name not in reg._names_to_collectors:          # type: ignore[attr-defined]
        Histogram(prom_name, doc, labels, registry=reg)
    _map(reg, prom_name, reg._names_to_collectors[prom_name])      # type: ignore[attr-defined]


def _ensure_summary(
    reg: CollectorRegistry,
    prom_name: str,
    doc: str,
    labels: List[str],
) -> None:
    if prom_name not in reg._names_to_collectors:          # type: ignore[attr-defined]
        Summary(prom_name, doc, labels, registry=reg)
    _map(reg, prom_name, reg._names_to_collectors[prom_name])      # type: ignore[attr-defined]


def _ensure_gauge(reg: CollectorRegistry, prom_name: str, doc: str) -> None:
    if prom_name not in reg._names_to_collectors:          # type: ignore[attr-defined]
        Gauge(prom_name, doc, registry=reg)
    _map(reg, prom_name, reg._names_to_collectors[prom_name])      # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def register_metrics(registry: CollectorRegistry) -> None:
    """不足分のみを登録（重複例外は発生しない）"""

    # ---- PoH issuance -------------------------------------------------------
    _ensure_counter(registry, "poh_issued", "Total PoH issued", ["result"])
    _ensure_histogram(
        registry,
        "poh_issue_latency_seconds",
        "PoH issuance latency (histogram)",
        ["result"],
    )
    _ensure_summary(
        registry,
        "poh_issue_latency_summary_seconds",
        "PoH issuance latency (summary)",
        ["result"],
    )

    # ---- PoH verification ---------------------------------------------------
    _ensure_histogram(
        registry,
        "poh_verify_latency_seconds",
        "PoH verification latency (histogram)",
        ["result"],
    )
    _ensure_summary(
        registry,
        "poh_verify_latency_summary_seconds",
        "PoH verification latency (summary)",
        ["result"],
    )

    # ---- GC / peers ---------------------------------------------------------
    _ensure_counter(
        registry,
        "gc_events",
        "Number of garbage-collection events",
        ["type"],
    )
    _ensure_gauge(registry, "active_peers", "Number of currently active peers")

    # ---- HTTP / gRPC --------------------------------------------------------
    _ensure_counter(
        registry,
        "http_requests",
        "Total number of HTTP requests",
        ["method", "endpoint", "status"],
    )
    _ensure_counter(
        registry,
        "grpc_requests",
        "Total number of gRPC requests",
        ["method", "code"],
    )


def get_metric(name: str, registry: CollectorRegistry):
    """
    family 名（例: 'poh_issued_total'）で Metric オブジェクトを返す。
    無ければ register_metrics() で自動登録してから取得。
    """
    if registry not in _REGISTERED or name not in _REGISTERED[registry]:
        register_metrics(registry)
    return _REGISTERED[registry][name]
