# D:\city_chain_project\Algorithm\PoP\pop_python\polygons.py

"""
pop_polygons.py

Shapely を使って多数の市町村ポリゴンを高速に検索。
STRtree でポリゴンを空間インデックス化。
"""

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

# city_id -> list of (lat,lon)
CITY_POLYGON_DATA = {
    "cityA": [(35.0,139.0),(35.05,139.0),(35.05,139.05),(35.0,139.05)],
    "cityB": [(40.7,-74.0),(40.75,-74.0),(40.75,-73.95),(40.7,-73.95)]
    # ...本番では数百/数千市町村分
}

# このdictは city_id -> shapely Polygon
CITY_POLYGONS = {}
# STRtree 用のリスト [ (Polygon, city_id), ... ]
CITY_POLYGON_OBJECTS = []
STR_TREE = None

def load_city_polygons():
    """
    アプリ起動時に呼び出し。
    CITY_POLYGON_DATA をもとに、Polygonオブジェクトを作成し、
    STRtreeに登録する。
    """
    global CITY_POLYGONS, CITY_POLYGON_OBJECTS, STR_TREE

    CITY_POLYGONS.clear()
    CITY_POLYGON_OBJECTS.clear()

    for city_id, coords in CITY_POLYGON_DATA.items():
        # shapely: (x,y)=(lon,lat)
        poly = Polygon([(lon,lat) for (lat,lon) in coords])
        CITY_POLYGONS[city_id] = poly
        CITY_POLYGON_OBJECTS.append((poly, city_id))

    # STRtree の構築: 
    #  Shapely 2.0 以降は geometry のみを受け取れるので、(geometry, id) 形式は工夫が必要
    #  ここでは geometry だけを集め、並行して city_id を別リスト管理
    polys_only = [item[0] for item in CITY_POLYGON_OBJECTS]
    STR_TREE = STRtree(polys_only)

def find_city_by_location(lat, lon):
    """
    STRtree で高速に city_id を検索する。
    1) Point(lon,lat)
    2) STRtree.query(point) で候補polygonを絞る
    3) その中で contains(point) を確かめる
    """
    if STR_TREE is None:
        # fallback => 直線検索
        return _legacy_find_city(lat, lon)

    point = Point(lon, lat)
    candidates = STR_TREE.query(point)  # これで候補Polygonのリスト

    for candidate_poly in candidates:
        # city_id を CITY_POLYGON_OBJECTS から探す => index
        #  Shapely 2.0 では geometry そのものを比較してインデックスを特定
        #  (あくまでもサンプル)
        if candidate_poly.contains(point):
            # city_idを得る
            # city_idは CITY_POLYGON_OBJECTS のうち candidate_poly に対応するものを探す
            # 雑実装: ループ
            for (poly, cid) in CITY_POLYGON_OBJECTS:
                if poly == candidate_poly:
                    return cid
    return None

def _legacy_find_city(lat, lon):
    """
    STRtreeが未初期化の場合の fallback
    """
    point = Point(lon, lat)
    for city_id, poly in CITY_POLYGONS.items():
        if poly.contains(point):
            return city_id
    return None
