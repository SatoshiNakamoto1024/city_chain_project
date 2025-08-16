# D:\city_chain_project\network\DAGs\common\reward\geo.py
"""
geo utilities … Haversine + 重み付きスコア計算
"""
from __future__ import annotations
import math

EARTH_R = 6371.0  # km


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """2 点間の距離 (km)"""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return 2 * EARTH_R * math.asin(math.sqrt(a))
