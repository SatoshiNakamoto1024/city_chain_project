# D:\city_chain_project\Algorithm\PoP\pop_python\__init__.py
# -*- coding: utf-8 -*-
"""
pop_python パッケージ
Proof-of-Presence 用の高レベル Python API
"""
__version__ = "0.1.0"
import sys, os, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# まず Python 実装をインポート
from pop_python.manager      import initialize_pop_system, get_place_info_and_bonus
from pop_python.polygons     import load_city_polygons, find_city_by_location
from pop_python.events       import check_city_event, check_location_event
from pop_python.localization import get_mobile_location

# 可能であれば Rust 拡張を動的に置き換え
try:
    import pop_rust as _rust
except ImportError:
    _rust = None

if _rust is not None:
    if hasattr(_rust, "load_polygons_from_dir"):
        load_city_polygons = _rust.load_polygons_from_dir
    if hasattr(_rust, "query_point"):
        find_city_by_location = _rust.query_point
    if hasattr(_rust, "check_city_event"):
        check_city_event = _rust.check_city_event
    if hasattr(_rust, "check_location_event"):
        check_location_event = _rust.check_location_event
