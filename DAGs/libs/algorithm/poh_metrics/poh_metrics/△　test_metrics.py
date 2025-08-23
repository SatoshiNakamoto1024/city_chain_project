# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_metrics.py
import pytest
from prometheus_client import CollectorRegistry
from poh_metrics.registry import get_registry
import poh_metrics.metrics as metrics


@pytest.fixture(autouse=True)
def clear_and_reinit_registry(monkeypatch):
    """
    各テスト前に空の CollectorRegistry を差し替え、
    メトリクスを再登録できる状態にする。
    """
    # 新規レジストリ作成
    reg = CollectorRegistry()
    # 内部シングルトンを差し替え
    from poh_metrics import registry
    monkeypatch.setattr(registry, "_REGISTRY", reg)
    # メトリクス登録（force=True で再登録）
    metrics.register_metrics(reg, force=True)
    return reg


def test_metrics_registered():
    """
    必要なメトリクス名がすべてレジストリに含まれていること。
    """
    reg = get_registry()
    names = {mf.name for mf in reg.collect()}

    expected = {
        # PoH issuance
        "poh_issued_total",
        "poh_issue_latency_seconds",
        "poh_issue_latency_summary_seconds",
        # PoH verification
        "poh_verify_latency_seconds",
        "poh_verify_latency_summary_seconds",
        # Garbage collection
        "gc_events_total",
        # Active peers
        "active_peers",
        # HTTP/gRPC requests
        "http_requests_total",
        "grpc_requests_total",
    }

    missing = expected - names
    assert not missing, f"Missing metrics: {missing}"
