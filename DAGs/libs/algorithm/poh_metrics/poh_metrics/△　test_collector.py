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
async def test_collector_functions(monkeypatch):
    # テスト用にレジストリを新規作成し、初期化
    test_reg = CollectorRegistry()
    register_metrics(test_reg)

    # PoH 発行・検証・GC・ピア更新を実行
    await increment_poh("success", test_reg)
    await observe_verify("failure", 0.123, test_reg)
    await record_gc("minor", 2, test_reg)
    await set_active_peers(5, test_reg)

    # レジストリから全 MetricFamily を取得
    fams = {f.name: f for f in test_reg.collect()}

    # Counter: poh_issued_total
    samples = [
        s.value
        for s in fams["poh_issued_total"].samples
        if s.labels.get("result") == "success"
    ]
    assert samples and samples[0] >= 1

    # Histogram: poh_verify_latency_seconds
    hist = fams["poh_verify_latency_seconds"]
    assert any(s.labels.get("result") == "failure" for s in hist.samples)

    # Counter: gc_events_total
    gc_counter = fams["gc_events_total"]
    assert any(s.labels.get("type") == "minor" for s in gc_counter.samples)

    # Gauge: active_peers
    gauge = fams["active_peers"]
    vals = [s.value for s in gauge.samples]
    assert vals and vals[0] == 5
