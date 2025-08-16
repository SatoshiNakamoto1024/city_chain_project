# D:\city_chain_project\Algorithm\PoP\pop_python\events.py
# -*- coding: utf-8 -*-
"""
時間帯／位置イベントによるボーナスマルチプライヤ計算。
定義は外部 JSON（config/city_events.json, config/location_events.json）から
動的にロードし、管理者画面からの追加にも対応します。
"""
import os
import json
import time
from shapely.geometry import Point, Polygon
from typing import List, Dict, Any, Optional

# ────────────────────────────────────────────────────────────────
# 外部設定ファイルのパス
# ────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CITY_EVENTS_FILE     = os.path.join(CONFIG_DIR, "city_events.json")
LOCATION_EVENTS_FILE = os.path.join(CONFIG_DIR, "location_events.json")


def _load_json(path: str) -> List[Dict[str, Any]]:
    """指定パスの JSON ファイルを読み込み、存在しなければ空リストを返す"""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: List[Dict[str, Any]]) -> None:
    """指定パスへ JSON ファイルを書き出す（ディレクトリ自動作成）"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ────────────────────────────────────────────────────────────────
# 起動時に一度だけロード
# ────────────────────────────────────────────────────────────────
CITY_BONUS_EVENTS: List[Dict[str, Any]]     = _load_json(CITY_EVENTS_FILE)
LOCATION_BONUS_EVENTS: List[Dict[str, Any]] = _load_json(LOCATION_EVENTS_FILE)


# ────────────────────────────────────────────────────────────────
# ボーナスマルチプライヤ計算
# ────────────────────────────────────────────────────────────────
def check_city_event(city_id: Optional[str]) -> float:
    """
    city_id に対応するイベントを走査し、現在時刻が active_start～active_end
    内であれば multiplier を返す。ヒットしなければ 1.0。
    """
    now = time.time()
    for ev in CITY_BONUS_EVENTS:
        if ev.get("city_id") == city_id and ev["active_start"] <= now <= ev["active_end"]:
            return float(ev.get("multiplier", 1.0))
    return 1.0


def check_location_event(lat: float, lon: float) -> float:
    """
    ポリゴンイベントを走査し、Point(lon,lat) がその中にあれば multiplier を返す。
    ヒットしなければ 1.0。
    """
    now = time.time()
    pt = Point(lon, lat)
    for ev in LOCATION_BONUS_EVENTS:
        if ev["active_start"] <= now <= ev["active_end"]:
            poly = Polygon(ev["coordinates"])
            if poly.contains(pt):
                return float(ev.get("multiplier", 1.0))
    return 1.0


# ────────────────────────────────────────────────────────────────
# 管理画面からのイベント追加 API 用
# ────────────────────────────────────────────────────────────────
def add_city_event(ev: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    新しい市町村イベントを追加し、ファイルとグローバル変数を更新。
    ev のキー例:
      {
        "city_id": str,
        "active_start": int,
        "active_end":   int,
        "multiplier":   float,
        "action":       str,
        "target":       Optional[str],
        "description":  Optional[str],
      }
    """
    events = _load_json(CITY_EVENTS_FILE)
    events.append(ev)
    _save_json(CITY_EVENTS_FILE, events)
    global CITY_BONUS_EVENTS
    CITY_BONUS_EVENTS = events
    return CITY_BONUS_EVENTS


def add_location_event(ev: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    新しいポリゴンイベントを追加し、ファイルとグローバル変数を更新。
    ev のキー例:
      {
        "coordinates": [[lon, lat], ...],
        "active_start": int,
        "active_end":   int,
        "multiplier":   float,
        "action":       str,
        "target":       Optional[str],
        "description":  Optional[str],
      }
    """
    events = _load_json(LOCATION_EVENTS_FILE)
    events.append(ev)
    _save_json(LOCATION_EVENTS_FILE, events)
    global LOCATION_BONUS_EVENTS
    LOCATION_BONUS_EVENTS = events
    return LOCATION_BONUS_EVENTS
