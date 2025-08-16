# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_metrics.py

import pytest
from prometheus_client import CollectorRegistry

from poh_metrics.metrics import register_metrics


def test_metrics_registered():
    reg = CollectorRegistry()
    register_metrics(reg)

    # .collect() で返る MetricFamily 名は _total のつかない名前！
    names = {mf.name for mf in reg.collect()}

    expected = {
        "poh_issued",
        "poh_issue_latency_seconds",
        "poh_issue_latency_summary_seconds",
        "poh_verify_latency_seconds",
        "poh_verify_latency_summary_seconds",
        "gc_events",
        "active_peers",
        "http_requests",
        "grpc_requests",
    }

    assert expected.issubset(names)
