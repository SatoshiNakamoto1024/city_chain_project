# pop_python/geolocation/__init__.py
# -*- coding: utf-8 -*-
"""
Geolocation サブモジュール: GPS/Wi-Fi/モック位置取得機能をまとめたパッケージ
"""
import sys
import os
import base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from geolocation.gps_handler import validate_gps
from geolocation.wifi_handler import estimate_location_by_wifi
from geolocation.location_fallback import generate_mock_location
from geolocation.app_geolocation import app as geolocation_app

__all__ = [
    "estimate_location_by_wifi",
    "generate_mock_location",
    "geolocation_app",
    "validate_gps",
]
