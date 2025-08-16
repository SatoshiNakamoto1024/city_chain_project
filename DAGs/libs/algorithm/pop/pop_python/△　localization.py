# D:\city_chain_project\Algorithm\PoP\pop_python\localization.py
# pop_python/localization.py
# -*- coding: utf-8 -*-
"""
端末からの位置情報取得ロジック。
ユーザー指定がなければ、ロード済みのすべての都市ポリゴンから
ランダムに１つ選び、内部を一様にサンプリングして返します。
"""
import sys, os, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
from typing import Tuple, Optional
from shapely.geometry import Point
from pop_python.polygons import load_city_polygons, city_polygons, city_ids

def get_mobile_location(
    user_id: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Tuple[float, float, str]:
    """
    - lat, lon が与えられればそのまま返す (method="UserProvided")
    - None の場合は、
        1) city_polygons が空ならロード
        2) city_ids と city_polygons を並列してランダム選択
        3) 選んだポリゴン内を一様サンプリング
        4) (lat, lon, method="MockRandomCity:<city_id>") を返す
    """
    # １．ユーザー指定があればそれを使う
    if lat is not None and lon is not None:
        return lat, lon, "UserProvided"

    # ２．ポリゴン未ロードならロード
    if not city_polygons:
        load_city_polygons()

    # ３．ポリゴンが１つもないならフォールバック
    if not city_polygons:
        return 0.0, 0.0, "MockRandom"

    # ４．都市ポリゴンをランダム選択
    idx = random.randrange(len(city_polygons))
    poly = city_polygons[idx]
    cid  = city_ids[idx]

    # ５．バウンディングボックス内を一様サンプリング
    minx, miny, maxx, maxy = poly.bounds
    while True:
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        if poly.contains(Point(x, y)):
            # shapely Point(x,y) は (lon,lat) 順なので、このままだと逆になる
            return y, x, f"MockRandomCity:{cid}"
