# D:\city_chain_project\Algorithm\PoP\pop_python\geolocation\test_geolocation.py
# -*- coding: utf-8 -*-
"""
geolocation サブモジュールの総合テスト
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from fastapi.testclient import TestClient
from pop_python.geolocation.gps_handler import validate_gps
import pop_python.geolocation.wifi_handler as wifi_handler
from pop_python.geolocation.location_fallback import generate_mock_location
from pop_python.geolocation.app_geolocation import app as geo_app

client = TestClient(geo_app)


# ───────────────────────── GPS ─────────────────────────
def test_validate_gps_valid():
    assert validate_gps(0, 0)
    assert validate_gps(90, 180)
    assert validate_gps(-90, -180)


def test_validate_gps_invalid():
    assert not validate_gps(91, 0)
    assert not validate_gps(0, 181)


# ──────────────────────── Wi-Fi core ───────────────────
@pytest.mark.parametrize("url,key", [(None, None), ("", "")])
def test_estimate_location_by_wifi_no_env(monkeypatch, url, key):
    monkeypatch.delenv("GEOLOCATION_API_URL", raising=False)
    monkeypatch.delenv("GEOLOCATION_API_KEY", raising=False)
    assert wifi_handler.estimate_location_by_wifi([{"mac": "aa"}]) is None


class DummyResp:
    def __init__(self, data):
        self._data = data; self.status_code = 200

    def raise_for_status(self): pass
    def json(self): return self._data


def test_estimate_location_by_wifi_success(monkeypatch):
    monkeypatch.setenv("GEOLOCATION_API_URL", "http://example.com")
    monkeypatch.setenv("GEOLOCATION_API_KEY", "key")
    monkeypatch.setattr(wifi_handler.requests, "post",
                        lambda url, json, timeout: DummyResp({"location": {"lat": 12.34, "lng": 56.78}}))
    assert wifi_handler.estimate_location_by_wifi([{"mac": "00"}]) == (12.34, 56.78)


# ───────────────────── モック位置 ─────────────────────
def test_generate_mock_location(monkeypatch):
    # 数学上安全に 1ポリゴンも無いケースを強制
    monkeypatch.setattr("pop_python.polygons.city_polygons", [])
    lat, lon, method = generate_mock_location()
    assert method.startswith("MockRandomCity:")


# ─────────────────── FastAPI endpoints ─────────────────
def test_gps_endpoint_success():
    r = client.post("/gps", json={"lat": 35.0, "lon": 139.0})
    assert r.status_code == 200 and r.json()["method"] == "GPS"


def test_gps_endpoint_fail():
    assert client.post("/gps", json={"lat": 999, "lon": 999}).status_code == 400


def test_wifi_endpoint_success(monkeypatch):
    monkeypatch.setenv("GEOLOCATION_API_URL", "x"); monkeypatch.setenv("GEOLOCATION_API_KEY", "x")
    monkeypatch.setattr(wifi_handler.requests, "post",
                        lambda *a, **k: DummyResp({"location": {"lat": 1.2, "lng": 3.4}}))
    r = client.post("/wifi", json={"wifi_data": [{"mac": "00", "rssi": -50}]})
    assert r.status_code == 200 and r.json()["method"] == "WiFi"


def test_wifi_endpoint_not_found(monkeypatch):
    monkeypatch.delenv("GEOLOCATION_API_URL", raising=False)
    monkeypatch.delenv("GEOLOCATION_API_KEY", raising=False)
    r = client.post("/wifi", json={"wifi_data": [{"mac": "aa"}]})
    assert r.status_code == 404


def test_mock_endpoint():
    assert client.get("/mock").status_code == 200
