# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_registry.py
import pytest
from prometheus_client import CollectorRegistry
from poh_metrics.registry import get_registry, set_registry, push_metrics

def test_singleton_registry():
    # get_registry() は同じオブジェクトを返す
    r1 = get_registry()
    r2 = get_registry()
    assert isinstance(r1, CollectorRegistry)
    assert r1 is r2

def test_set_and_push_metrics(monkeypatch):
    # テスト用レジストリを新規作成して差し替え
    test_reg = CollectorRegistry()
    set_registry(test_reg)
    # push_to_gateway をフック
    called = {}
    def fake_push(gateway, job, registry):
        called["args"] = (gateway, job, registry)

    monkeypatch.setattr("poh_metrics.registry.push_to_gateway", fake_push)

    # push_metrics 呼び出し
    push_metrics("http://localhost:9091", "job1")

    assert called["args"][0] == "http://localhost:9091"
    assert called["args"][1] == "job1"
    # 差し替えたレジストリが渡されていること
    assert called["args"][2] is test_reg
