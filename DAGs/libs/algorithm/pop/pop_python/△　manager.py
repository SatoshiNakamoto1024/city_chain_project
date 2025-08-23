# D:\city_chain_project\Algorithm\PoP\pop_python\manager.py
# -*- coding: utf-8 -*-
"""
PoP マネージャ:
  - ポリゴンロード
  - キャッシュ lookup
  - イベントボーナス合成
  - 位置取得
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functools import lru_cache
from typing import TypedDict
from pop_python.polygons import load_city_polygons, find_city_by_location
from pop_python.events import check_city_event, check_location_event
from pop_python.localization import get_mobile_location

INITIALIZED = False


class PlaceInfo(TypedDict):
    lat: float
    lon: float
    city_id: str | None
    multiplier: float
    method: str


def initialize_pop_system() -> None:
    global INITIALIZED
    load_city_polygons()
    INITIALIZED = True


@lru_cache(maxsize=1024)
def _cached_lookup(user_id: str, lat: float, lon: float):
    city = find_city_by_location(lat, lon)
    city_mult = check_city_event(city)
    loc_mult = check_location_event(lat, lon)
    return city, city_mult * loc_mult


def get_place_info_and_bonus(
    user_id: str,
    lat: float | None = None,
    lon: float | None = None
) -> PlaceInfo:
    if not INITIALIZED:
        initialize_pop_system()
    lat_, lon_, method = get_mobile_location(user_id, lat, lon)
    city, mult = _cached_lookup(user_id, round(lat_, 5), round(lon_, 5))
    return {
        "lat": lat_,
        "lon": lon_,
        "city_id": city,
        "multiplier": mult,
        "method": method,
    }
