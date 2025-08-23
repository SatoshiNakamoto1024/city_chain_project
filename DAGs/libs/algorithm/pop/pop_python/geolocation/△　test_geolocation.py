# D:\city_chain_project\Algorithm\PoP\pop_python\geolocation\test_geolocation.py
# -*- coding: utf-8 -*-
"""
geolocation サブモジュールの単体テスト
GPS, Wi-Fi, モック、FastAPI エンドポイントを網羅します。
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import random
import pytest
from fastapi.testclient import TestClient

from pop_python.geolocation.gps_handler import validate_gps
import pop_python.geolocation.wifi_handler as wifi_handler
from pop_python.geolocation.location_fallback import generate_mock_location
from pop_python.geolocation.app_geolocation import app as geo_app
from pop_python.polygons import load_city_polygons, city_polygons

client = TestClient(geo_app)


# --- GPS テスト ---
def test_validate_gps_valid():
    assert validate_gps(0.0, 0.0)
    assert validate_gps(90.0, 180.0)
    assert validate_gps(-90.0, -180.0)


def test_validate_gps_invalid():
    assert not validate_gps(91.0, 0.0)
    assert not validate_gps(0.0, 181.0)


# --- Wi-Fi テスト ---
@pytest.mark.parametrize("env_url,env_key", [(None, None), ("", "")])
def test_estimate_location_by_wifi_no_env(monkeypatch, env_url, env_key):
    # 環境変数が設定されていない／空文字なら None を返す
    monkeypatch.delenv("GEOLOCATION_API_URL", raising=False)
    monkeypatch.delenv("GEOLOCATION_API_KEY", raising=False)
    assert wifi_handler.estimate_location_by_wifi([{"mac": "aa"}]) is None


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception("HTTP Error")

    def json(self):
        return self._json


def test_estimate_location_by_wifi_success(monkeypatch):
    # 環境変数を設定
    monkeypatch.setenv("GEOLOCATION_API_URL", "http://example.com")
    monkeypatch.setenv("GEOLOCATION_API_KEY", "dummy_key")
    # モックレスポンス
    dummy = DummyResponse({"location": {"lat": 12.34, "lng": 56.78}})
    monkeypatch.setattr(wifi_handler.requests, "post", lambda url, json, timeout: dummy)
    latlng = wifi_handler.estimate_location_by_wifi([
        {"mac": "00:11:22:33:44:55", "ssid": "X", "rssi": -50}
    ])
    assert latlng == (12.34, 56.78)


# --- モック位置テスト ---
def test_generate_mock_location(monkeypatch):
    # ポリゴンをロード
    load_city_polygons()
    # 1番目を選ぶ
    monkeypatch.setattr(random, "randrange", lambda n: 0)
    # 常に min 値を返す
    monkeypatch.setattr(random, "uniform", lambda a, b: a)
    lat, lon, method = generate_mock_location()
    assert method.startswith("MockRandomCity:")
    # 座標がポリゴン内
    poly = city_polygons[0]
    minx, miny, maxx, maxy = poly.bounds
    assert miny <= lat <= maxy
    assert minx <= lon <= maxx

# --- FastAPI エンドポイントテスト ---


def test_gps_endpoint_success():
    resp = client.post("/gps", json={"lat": 36.3, "lon": 136.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["method"] == "GPS"


def test_gps_endpoint_fail():
    resp = client.post("/gps", json={"lat": 1000, "lon": 2000})
    assert resp.status_code == 400


def test_wifi_endpoint_success(monkeypatch):
    # 環境変数とレスポンスモック
    monkeypatch.setenv("GEOLOCATION_API_URL", "http://example.com")
    monkeypatch.setenv("GEOLOCATION_API_KEY", "dummy_key")

    class Resp:
        def __init__(self): self.status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"location": {"lat": 1.2, "lng": 3.4}}
    monkeypatch.setattr(wifi_handler.requests, "post", lambda url, json, timeout: Resp())
    resp = client.post("/wifi", json={"wifi_data": [{"mac": "00:11:22:33:44:55", "rssi": -50}]})
    assert resp.status_code == 200
    assert resp.json()["method"] == "WiFi"


def test_wifi_endpoint_not_found():
    # 環境変数なし
    os.environ.pop("GEOLOCATION_API_URL", None)
    os.environ.pop("GEOLOCATION_API_KEY", None)
    resp = client.post("/wifi", json={"wifi_data": [{"mac": "foo"}]})
    assert resp.status_code == 404


def test_mock_endpoint():
    resp = client.get("/mock")
    assert resp.status_code == 200
    data = resp.json()
    assert data["method"].startswith("MockRandom")
