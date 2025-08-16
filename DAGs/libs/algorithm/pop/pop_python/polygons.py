# D:\city_chain_project\Algorithm\PoP\pop_python\polygons.py
# -*- coding: utf-8 -*-
"""
GeoJSON ファイル群を動的に読み込み、STRtree 空間インデックスを構築して高速検索。
Shapely 2.x では STRtree.query が整数インデックス（numpy.int64）を返す場合があるため、
それに対応して city_id を取得します。
"""
import os
import glob
import json
import numpy as np
from shapely.geometry import shape, Point, Polygon
from shapely.strtree import STRtree
from typing import Optional, List, Union

# polygon_data ディレクトリ（pop_python の一つ上）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLY_DIR = os.path.join(BASE_DIR, "polygon_data")

# グローバルキャッシュ
city_ids: List[str] = []
city_polygons: List[Polygon] = []
geom_to_city: dict[Polygon, str] = {}
_str_tree: Optional[STRtree] = None

def load_city_polygons() -> None:
    """
    一度呼び出せば OK。
    Algorithm/PoP/polygon_data/*.geojson をすべて読み込み、
    city_polygons, geom_to_city, _str_tree を構築します。
    """
    global city_ids, city_polygons, geom_to_city, _str_tree

    city_ids = []
    city_polygons = []
    geom_to_city = {}

    pattern = os.path.join(POLY_DIR, "*.geojson")
    for path in glob.glob(pattern):
        with open(path, encoding="utf-8") as f:
            gj = json.load(f)
        for feat in gj.get("features", []):
            props = feat.get("properties", {}) or {}
            city_id = props.get("id") or props.get("name") or os.path.splitext(os.path.basename(path))[0]
            geom = feat.get("geometry")
            if not geom or geom.get("type") != "Polygon":
                continue
            poly = shape(geom)
            city_ids.append(city_id)
            city_polygons.append(poly)
            geom_to_city[poly] = city_id

    _str_tree = STRtree(city_polygons)

def find_city_by_location(lat: float, lon: float) -> Optional[str]:
    """
    Point(lon,lat) が属する city_id を返します。
    STRtree.query の結果が整数インデックス（numpy.int64）でも
    直接 Polygon オブジェクトでも対応します。
    """
    global _str_tree
    if _str_tree is None:
        load_city_polygons()

    pt = Point(lon, lat)
    candidates: Union[List[Polygon], List[int]] = _str_tree.query(pt)

    for candidate in candidates:
        # numpy.int64 も含めインデックス判定
        if isinstance(candidate, (int, np.integer)):
            poly = city_polygons[int(candidate)]
        else:
            poly = candidate
        
        city_id = geom_to_city.get(poly)
        if city_id and poly.contains(pt):
            return city_id

    return None