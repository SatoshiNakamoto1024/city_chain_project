# D:\city_chain_project\Algorithm\PoP\pop_python\geolocation\location_fallback.py
# -*- coding: utf-8 -*-
"""
ポリゴン内ランダムサンプリング — polygon_data/*.geojson が空でも動作
"""
import sys, os, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import random
from shapely.geometry import Point
from pop_python.polygons import load_city_polygons, city_polygons, city_ids


def generate_mock_location() -> tuple[float, float, str]:
    """
    • city_polygons がある → “MockRandomCity:<city_id>”
    • 無い → “MockRandomCity:Unknown”
    """
    if not city_polygons:
        load_city_polygons()

    if not city_polygons:                        # geojson 未配置など
        return 0.0, 0.0, "MockRandomCity:Unknown"

    idx  = random.randrange(len(city_polygons))
    poly = city_polygons[idx]
    cid  = city_ids[idx]
    minx, miny, maxx, maxy = poly.bounds

    while True:
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        if poly.contains(Point(x, y)):
            return y, x, f"MockRandomCity:{cid}"
