# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_collector.py

import pytest
from prometheus_client import CollectorRegistry

from poh_metrics.collector import (
    increment_poh,
    observe_verify,
    record_gc,
    set_active_peers,
)
from poh_metrics.metrics import register_metrics


@pytest.mark.asyncio
async def test_collector_functions():
    # テスト専用の Registry
    reg = CollectorRegistry()
    register_metrics(reg)  # 1 回だけ初期登録

    # 各操作
    await increment_poh("success", reg)
    await observe_verify("failure", 0.123, reg)
    await record_gc("minor", 2, reg)
    await set_active_peers(5, reg)

    # collect() で取れる MetricFamily は Counter なら "_total" を除いた名前！
    fams = {f.name: f for f in reg.collect()}

    # Counter (→ poh_issued_total → .collect() name は poh_issued)
    assert any(
        s.value >= 1 and s.labels.get("result") == "success"
        for s in fams["poh_issued"].samples
    )

    # Histogram
    assert any(
        s.labels.get("result") == "failure"
        for s in fams["poh_verify_latency_seconds"].samples
    )

    # GC Counter (→ gc_events_total → .collect() name は gc_events)
    assert any(
        s.labels.get("type") == "minor"
        for s in fams["gc_events"].samples
    )

    # Gauge
    assert fams["active_peers"].samples[0].value == 5
