# D:\city_chain_project\Algorithm\PoP\pop_python\geolocation\wifi_handler.py
# -*- coding: utf-8 -*-
"""
Wi-Fi 情報から位置を推定するインターフェース
"""
from typing import List, Tuple, Optional
import os
import requests


def estimate_location_by_wifi(wifi_data: List[dict]) -> Optional[Tuple[float, float]]:
    """
    Wi-Fi サンプルを外部 Geolocation API に転送して (lat, lon) を返す。
    • 実行時に毎回 os.getenv で URL / KEY を取得するので、
      pytest の monkeypatch で環境変数を後からセットしても反映される。
    """
    api_url = os.getenv("GEOLOCATION_API_URL")
    api_key = os.getenv("GEOLOCATION_API_KEY")
    if not api_url or not api_key:
        return None

    payload = {"wifiAccessPoints": wifi_data, "key": api_key}
    try:
        resp = requests.post(api_url, json=payload, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        loc  = data.get("location", {})
        lat  = loc.get("lat")
        lng  = loc.get("lng")
        if lat is not None and lng is not None:
            return lat, lng
    except Exception:
        pass
    return None
