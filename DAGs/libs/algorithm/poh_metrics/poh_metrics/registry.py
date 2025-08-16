# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\registry.py
"""
poh_metrics.registry
====================
アプリ全体で共有する CollectorRegistry と
Prometheus Pushgateway 連携ユーティリティ。
"""

from __future__ import annotations
from typing import Optional

from prometheus_client import CollectorRegistry, push_to_gateway as _push
from .metrics import register_metrics

# モジュール内シングルトンインスタンス
_REGISTRY: Optional[CollectorRegistry] = None


def get_registry() -> CollectorRegistry:
    """
    グローバル Registry を返します。
    初回呼び出し時に新規生成し、メトリクスを登録します。
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = CollectorRegistry()
        register_metrics(_REGISTRY)
    return _REGISTRY


def set_registry(registry: Optional[CollectorRegistry] = None) -> None:
    """
    **テスト専用**: 内部レジストリを差し替えます。
    registry=None の場合は新規生成し、登録します。
    """
    global _REGISTRY
    _REGISTRY = registry if registry is not None else CollectorRegistry()
    register_metrics(_REGISTRY)


def push_metrics(gateway: str, job: str = "poh_job") -> None:
    """
    現在のレジストリを Pushgateway へ送信します。
    内部で自作ラッパー push_to_gateway() を経由するので、
    テスト時に monkeypatch しやすくなっています。
    """
    # ここを自前ラッパー経由にしておく
    push_to_gateway(gateway, job=job, registry=get_registry())


def push_to_gateway(
    gateway: str,
    job: str = "poh_job",
    registry: Optional[CollectorRegistry] = None,
) -> None:
    """
    prometheus_client.push_to_gateway の薄いラッパー。
    registry=None の場合は get_registry() を使います。
    """
    if registry is None:
        registry = get_registry()
    _push(gateway, job=job, registry=registry)


__all__ = ["get_registry", "set_registry", "push_metrics", "push_to_gateway"]
