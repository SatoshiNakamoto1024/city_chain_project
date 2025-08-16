# D:\city_chain_project\Algorithm\PoP\pop_python\app_pop.py
# -*- coding: utf-8 -*-
"""
FastAPI ベースの Proof-of-Presence API
+ 静的ファイル pop_event.html 配信
+ /pop エンドポイント
+ /events/* エンドポイント（取得・追加）
"""
import sys
import os
# pop_python パッケージを最優先で読み込む
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from pop_python.manager import get_place_info_and_bonus
from pop_python.events import (
    check_city_event,
    check_location_event,
    add_city_event,
    add_location_event,
    CITY_BONUS_EVENTS,
    LOCATION_BONUS_EVENTS,
)

app = FastAPI(title="Proof-of-Presence API")

# ─── CORS 設定 ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて絞り込んでください
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ─── static 配信 ─────────────────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─── /pop エンドポイント（既存） ─────────────────────────────────────────
class PopRequest(BaseModel):
    user_id: str
    lat: Optional[float] = Field(None, description="GPS 緯度")
    lon: Optional[float] = Field(None, description="GPS 経度")
    wifi_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Wi-Fi スキャン結果 (mac/rssi の dict のリスト)"
    )


class PlaceInfoResponse(BaseModel):
    lat: float
    lon: float
    city_id: Optional[str]
    multiplier: float
    method: str


@app.post("/pop", response_model=PlaceInfoResponse)
def pop_endpoint(req: PopRequest):
    try:
        info = get_place_info_and_bonus(
            req.user_id,
            req.lat,
            req.lon,
            req.wifi_data,
        )
        return PlaceInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── 市町村イベント API ───────────────────────────────────────────────────
@app.get("/events/city", response_model=List[Dict[str, Any]])
def get_city_events():
    """
    現在登録されている市町村イベント一覧を返す
    """
    return CITY_BONUS_EVENTS


@app.post("/events/city", response_model=List[Dict[str, Any]])
def post_city_event(ev: Dict[str, Any]):
    """
    1 件の市町村イベントを追加し、更新後の一覧を返す
    {
      "city_id": str,
      "active_start": int,
      "active_end":   int,
      "multiplier":   float,
      "action":       str,
      "target":       Optional[str],
      "description":  Optional[str],
    }
    """
    try:
        updated = add_city_event(ev)
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── ポリゴンイベント API ─────────────────────────────────────────────────
@app.get("/events/location", response_model=List[Dict[str, Any]])
def get_location_events():
    """
    現在登録されているポリゴンイベント一覧を返す
    """
    return LOCATION_BONUS_EVENTS


@app.post("/events/location", response_model=List[Dict[str, Any]])
def post_location_event(ev: Dict[str, Any]):
    """
    1 件のポリゴンイベントを追加し、更新後の一覧を返す
    {
      "coordinates": [[lon, lat], ...],
      "active_start": int,
      "active_end":   int,
      "multiplier":   float,
      "action":       str,
      "target":       Optional[str],
      "description":  Optional[str],
    }
    """
    try:
        updated = add_location_event(ev)
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
