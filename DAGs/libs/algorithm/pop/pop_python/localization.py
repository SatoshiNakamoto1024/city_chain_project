# D:\city_chain_project\Algorithm\PoP\pop_python\localization.py
"""
端末の位置情報取得ロジック

1. ユーザーが GPS(lat/lon) を渡せばそのまま返す     → method = "UserProvided"
2. Wi-Fi スキャン結果があれば外部 API で推定           → method = "WiFi"
3. いずれも無ければ polygon_data 内でランダムサンプリング → method = "MockRandom"
"""
from __future__ import annotations
from typing import Tuple, Optional, List, Dict
import random
import sys, os, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shapely.geometry import Point
import pop_python.polygons as poly_mod                    # 動的ロードのためモジュール単位で import
from pop_python.geolocation.gps_handler import validate_gps
from pop_python.geolocation.wifi_handler import estimate_location_by_wifi

# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def get_mobile_location(
    user_id: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    wifi_data: Optional[List[Dict]] = None,
) -> Tuple[float, float, str]:
    """
    Return (lat, lon, method)

    Parameters
    ----------
    user_id : str
        利用者 ID（キャッシュキー用）
    lat, lon : Optional[float]
        GPS から得られた緯度経度
    wifi_data : Optional[List[Dict]]
        Wi-Fi スキャン (mac, rssi などを含む辞書のリスト)

    Notes
    -----
    • GPS が来れば最優先で採用（method = "UserProvided"）
    • Wi-Fi が来れば estimate_location_by_wifi() → 成功で "WiFi"
    • どちらも無い場合 polygon_data/*.geojson からランダム位置 → "MockRandom"
    """
    # ─── 1) GPS ────────────────────────────────────────────────────
    if lat is not None and lon is not None:
        if not validate_gps(lat, lon):
            raise ValueError("Invalid GPS coordinates")
        return lat, lon, "UserProvided"

    # ─── 2) Wi-Fi 推定 ────────────────────────────────────────────
    if wifi_data:
        est = estimate_location_by_wifi(wifi_data)
        if est:
            lat_est, lon_est = est
            return lat_est, lon_est, "WiFi"

    # ─── 3) Mock（polygon_data からランダムサンプリング）──────────
    if not poly_mod.city_polygons:                      # 未ロードならロード
        poly_mod.load_city_polygons()

    if not poly_mod.city_polygons:                      # geojson 0 件
        return 0.0, 0.0, "MockRandom"

    idx  = random.randrange(len(poly_mod.city_polygons))
    poly = poly_mod.city_polygons[idx]
    minx, miny, maxx, maxy = poly.bounds

    # covers() は境界上も True。contains() だと境界点で無限ループの恐れ
    MAX_TRY = 1000
    for _ in range(MAX_TRY):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        if poly.covers(Point(x, y)):
            return y, x, "MockRandom"

    # 1000 回試しても見つからなければ (0,0) を返す
    return 0.0, 0.0, "MockRandom"
