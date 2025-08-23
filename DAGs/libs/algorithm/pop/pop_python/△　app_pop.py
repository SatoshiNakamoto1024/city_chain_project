# D:\city_chain_project\Algorithm\PoP\pop_python\app_pop.py
# -*- coding: utf-8 -*-
"""
FastAPI ベースの Proof-of-Presence API
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from pop_python.manager import get_place_info_and_bonus

app = FastAPI(title="Proof-of-Presence API")


class PopRequest(BaseModel):
    user_id: str
    lat: Optional[float] = Field(None, description="GPS 緯度")
    lon: Optional[float] = Field(None, description="GPS 経度")
    wifi_data: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Wi-Fi スキャン結果 (mac / rssi などの辞書のリスト)",
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
