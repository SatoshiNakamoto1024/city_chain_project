# D:\city_chain_project\Algorithm\PoP\pop_python\test_pop.py
# -*- coding: utf-8 -*-
import pytest
import sys
import os

# pop_python パッケージを必ずルート直下から読み込む
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from pop_python.manager  import get_place_info_and_bonus, initialize_pop_system
from pop_python.polygons import load_city_polygons, find_city_by_location
import pop_python.events as events


def test_find_city_by_location_direct():
    """GeoJSON からの直接検索テスト"""
    load_city_polygons()
    assert find_city_by_location(36.5720, 136.6460) == "kanazawa"
    assert find_city_by_location(48.8600,   2.3370) == "paris"
    assert find_city_by_location(0.0,       0.0   ) is None


def test_get_place_info_and_bonus_user_provided():
    """GPS 指定→UserProvided メソッド＋倍率 1.0"""
    initialize_pop_system()
    info = get_place_info_and_bonus("user1", 36.5720, 136.6460)
    assert info["city_id"]     == "kanazawa"
    assert pytest.approx(info["multiplier"]) == 1.0
    assert info["method"]      == "UserProvided"


def test_get_place_info_and_bonus_random(monkeypatch):
    """GPS/WiFi なし→MockRandom メソッド＋倍率 1.0"""
    # ポリゴン内サンプリングが必ず (0,0) になるよう固定
    monkeypatch.setattr(
        "pop_python.localization.random.uniform",
        lambda a, b: 0.0
    )
    initialize_pop_system()
    info = get_place_info_and_bonus("user2")
    assert info["city_id"]     is None
    assert pytest.approx(info["multiplier"]) == 1.0
    assert info["method"]      == "MockRandom"


def test_check_city_event(monkeypatch):
    """
    CITY_BONUS_EVENTS を差し替えて city_id ごとの
    マルチプライヤが動的に切り替わることを検証
    """
    # テスト用イベント定義
    start, end = 1_000.0, 2_000.0
    events.CITY_BONUS_EVENTS = [
        {
            "city_id":      "testcity",
            "active_start": start,
            "active_end":   end,
            "multiplier":   3.5,
        }
    ]

    # イベント期間中をシミュレート
    monkeypatch.setattr(events.time, "time", lambda: 1_500.0)
    assert events.check_city_event("testcity") == pytest.approx(3.5)
    # 他の city は影響なし
    assert events.check_city_event("other") == pytest.approx(1.0)

    # イベント期間外をシミュレート
    monkeypatch.setattr(events.time, "time", lambda: 3_000.0)
    assert events.check_city_event("testcity") == pytest.approx(1.0)


def test_check_location_event(monkeypatch):
    """
    LOCATION_BONUS_EVENTS を差し替えて緯度経度ごとの
    マルチプライヤが動的に切り替わることを検証
    """
    # テスト用イベント定義：単純な正方形ポリゴン
    start, end = 1_000.0, 2_000.0
    square = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
    events.LOCATION_BONUS_EVENTS = [
        {
            "coordinates":  square,
            "active_start": start,
            "active_end":   end,
            "multiplier":   4.2,
        }
    ]

    # イベント期間中かつポリゴン内
    monkeypatch.setattr(events.time, "time", lambda: 1_500.0)
    assert events.check_location_event(0.0, 0.0) == pytest.approx(4.2)
    # ポリゴン外は 1.0
    assert events.check_location_event(2.0, 2.0) == pytest.approx(1.0)

    # イベント期間外はポリゴン内でも 1.0
    monkeypatch.setattr(events.time, "time", lambda: 3_000.0)
    assert events.check_location_event(0.0, 0.0) == pytest.approx(1.0)
