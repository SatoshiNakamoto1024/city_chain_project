# D:\city_chain_project\Algorithm\PoP\test_pop_integration.py
# -*- coding: utf-8 -*-
"""
pop_python + pop_rust 統合テスト

※ 実行前に `maturin develop --release` などで pop_rust をインストール済みであること
"""
import sys
import importlib
import pytest
from pathlib import Path
from types import ModuleType

# ───────────────────────────────────────────────────────
# 1) pop_python パッケージを「PoP フォルダ直下」から必ず読み込む
# ───────────────────────────────────────────────────────
HERE = Path(__file__).parent.resolve()
# PoPフォルダ自体をパスに追加 (pop_python/ がサブフォルダとして見えるように)
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


# ───────────────────────────────────────────────────────
# 2) pop_rust の有無を __import__ で判定
# ───────────────────────────────────────────────────────
def _module_exists(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _module_exists("pop_rust"),
    reason="pop_rust wheel not installed"
)
def test_pop_rust_available():
    import pop_rust
    assert hasattr(pop_rust, "query_point")
    assert callable(pop_rust.query_point)


# ───────────────────────────────────────────────────────
# 3) pop_python を必ず再ロードする Fixture
# ───────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def pp() -> ModuleType:
    # すでにインポート済みなら消してから
    if "pop_python" in sys.modules:
        del sys.modules["pop_python"]
    return importlib.import_module("pop_python")


def _geojson_dir() -> str:
    # D:/…/Algorithm/PoP/polygon_data
    return str(HERE / "polygon_data")


# ───────────────────────────────────────────────────────
# 4) Rust バインディングが差し替わっているか検証
# ───────────────────────────────────────────────────────
def test_rust_binding_hijack(pp: ModuleType):
    import pop_rust
    # pop_python.find_city_by_location が pop_rust.query_point に一致するか
    assert pp.find_city_by_location is pop_rust.query_point


# ───────────────────────────────────────────────────────
# 5) 地名判定 (Rust) → Python API
# ───────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "lat,lon,expect_city",
    [
        (36.5720, 136.6460, "kanazawa"),
        (48.8600, 2.3370, "paris"),
        (0.0, 0.0, None),
    ],
)
def test_rust_query_from_python(pp: ModuleType, lat, lon, expect_city):
    import pop_rust as pr
    pr.load_polygons_from_dir(_geojson_dir())
    assert pp.find_city_by_location(lat, lon) == expect_city


# ───────────────────────────────────────────────────────
# 6) get_place_info_and_bonus の動作検証
# ───────────────────────────────────────────────────────
def test_get_place_info_with_gps(pp: ModuleType):
    pp.initialize_pop_system()
    info = pp.get_place_info_and_bonus("u1", 36.5720, 136.6460)
    assert info["city_id"] == "kanazawa"
    assert info["method"]  == "UserProvided"
    assert pytest.approx(info["multiplier"]) == 1.0


def test_get_place_info_with_wifi(pp: ModuleType, monkeypatch):
    # WiFi 推定をモック
    def fake_wifi(data):
        return (36.5720, 136.6460)
    monkeypatch.setattr(
        "pop_python.geolocation.wifi_handler.estimate_location_by_wifi",
        fake_wifi,
        raising=True
    )
    info = pp.get_place_info_and_bonus("u2", wifi_data=[{"mac": "00"}])
    assert info["city_id"] == "kanazawa"
    assert info["method"]  == "WiFi"
    assert pytest.approx(info["multiplier"]) == 1.0


def test_get_place_info_mock(pp: ModuleType, monkeypatch):
    # 乱数固定で必ず (0,0) を返す
    monkeypatch.setattr("pop_python.localization.random.uniform", lambda a, b: a)
    monkeypatch.setattr("pop_python.localization.random.randrange", lambda n: 0)
    info = pp.get_place_info_and_bonus("u3")
    assert info["city_id"] is None
    assert info["method"]  == "MockRandom"
    assert pytest.approx(info["multiplier"]) == 1.0
