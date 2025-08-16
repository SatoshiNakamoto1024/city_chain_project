# D:\city_chain_project\Algorithm\PoP\test_pop_integration.py
# -*- coding: utf-8 -*-
"""
pop_python + pop_rust 統合テスト

事前条件
* `pip install -e Algorithm/PoP/pop_python`
* `pip install Algorithm/PoP/dist/pop_rust-*.whl`
  （ソースフォルダ pop_rust_src は wheel 化後 rename しても OK）
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ────────────────────────────────
# 0. パス調整
# ────────────────────────────────
BASE = Path(__file__).resolve().parent          # …/Algorithm/PoP
SRC_POP_RUST = BASE / "pop_rust_src"            # wheel では不要なソース

# 1) pop_python を確実に import できるように
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))               # 先頭に入れるのが安全

# 2) wheel 版 pop_rust を使うため、ソースフォルダを sys.path から除外
if str(SRC_POP_RUST) in sys.path:
    sys.path.remove(str(SRC_POP_RUST))

# ────────────────────────────────
# ヘルパ
# ────────────────────────────────
def _compiled_pop_rust_loaded() -> bool:
    """
    wheel 由来の pop_rust が import 済みかどうかを判定
    （namespace モジュールだと query_point が無い）
    """
    try:
        import pop_rust  # noqa
        return hasattr(pop_rust, "query_point")
    except ImportError:
        return False


# ────────────────────────────────
# 1. pop_rust がロード出来るか
# ────────────────────────────────
@pytest.mark.skipif(not _compiled_pop_rust_loaded(), reason="pop_rust wheel not installed")
def test_pop_rust_available() -> None:
    import pop_rust  # noqa: F401
    assert hasattr(pop_rust, "query_point")


# ────────────────────────────────
# 2. pop_python を毎回クリーンに読み込む Fixture
# ────────────────────────────────
@pytest.fixture(scope="module")
def pp() -> ModuleType:
    sys.modules.pop("pop_python", None)        # キャッシュを消して再 import
    return importlib.import_module("pop_python")


# ────────────────────────────────
# 3. Rust バックエンドが差し替わったか
# ────────────────────────────────
def test_rust_binding_hijack(pp: ModuleType) -> None:
    import pop_rust

    assert pp.find_city_by_location is pop_rust.query_point


# ────────────────────────────────
# 4. ポリゴン検索（Rust） → Python から呼び出し
# ────────────────────────────────
GJ_DIR = BASE / "polygon_data"


@pytest.mark.parametrize(
    ("lat", "lon", "expect"),
    [(36.5720, 136.6460, "kanazawa"), (48.8600, 2.3370, "paris"), (0.0, 0.0, None)],
)
def test_rust_query(pp: ModuleType, lat: float, lon: float, expect: str | None) -> None:
    import pop_rust as pr

    pr.load_polygons_from_dir(str(GJ_DIR))
    assert pp.find_city_by_location(lat, lon) == expect


# ────────────────────────────────
# 5. get_place_info_and_bonus
# ────────────────────────────────
def test_get_place_info_gps(pp: ModuleType) -> None:
    pp.initialize_pop_system()
    info = pp.get_place_info_and_bonus("u1", 36.5720, 136.6460)
    assert info == {
        "lat": 36.5720,
        "lon": 136.6460,
        "city_id": "kanazawa",
        "multiplier": pytest.approx(1.0),
        "method": "UserProvided",
    }


def test_get_place_info_wifi(pp: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_wifi(_data):  # noqa: D401
        return 36.5720, 136.6460

    monkeypatch.setattr(
        "pop_python.localization.estimate_location_by_wifi",  # ★ コピー先をパッチ
        fake_wifi,
        raising=True,
    )

    info = pp.get_place_info_and_bonus("u2", wifi_data=[{"mac": "00"}])
    assert info["method"] == "WiFi"
    assert info["city_id"] == "kanazawa"
    assert pytest.approx(info["multiplier"]) == 1.0


def test_get_place_info_mock(pp: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pop_python.localization.random.uniform", lambda a, _b: a)
    monkeypatch.setattr("pop_python.localization.random.randrange", lambda _n: 0)

    info = pp.get_place_info_and_bonus("u3")
    assert info["method"] == "MockRandom"
    assert info["city_id"] is None
    assert pytest.approx(info["multiplier"]) == 1.0
