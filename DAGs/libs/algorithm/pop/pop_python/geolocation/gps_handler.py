# D:\city_chain_project\Algorithm\PoP\pop_python\geolocation\gps_handler.py
# -*- coding: utf-8 -*-
"""
GPS データの妥当性チェック
"""

def validate_gps(lat: float, lon: float) -> bool:
    """
    緯度経度が有効な範囲内かをチェックします
    """
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0