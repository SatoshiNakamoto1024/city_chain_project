# D:\city_chain_project\Algorithm\PoP\pop_python\geolocation\app_geolocation.py
# -*- coding: utf-8 -*-
"""
FastAPI エンドポイント定義
"""
import sys, os, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from geolocation.gps_handler import validate_gps
from geolocation.wifi_handler import estimate_location_by_wifi
from geolocation.location_fallback import generate_mock_location

app = FastAPI(title="Geolocation Service")


class GPSRequest(BaseModel):
    lat: float
    lon: float


class WiFiRequest(BaseModel):
    # 値の型は何でも許容 (mac= str, rssi= int など)
    wifi_data: List[Dict[str, Any]]


class GeolocateResp(BaseModel):
    lat: float
    lon: float
    method: str


@app.post("/gps", response_model=GeolocateResp)
def geolocate_gps(req: GPSRequest):
    if not validate_gps(req.lat, req.lon):
        raise HTTPException(status_code=400, detail="Invalid GPS coordinates")
    return GeolocateResp(lat=req.lat, lon=req.lon, method="GPS")


@app.post("/wifi", response_model=GeolocateResp)
def geolocate_wifi(req: WiFiRequest):
    est = estimate_location_by_wifi(req.wifi_data)
    if est is None:
        raise HTTPException(status_code=404, detail="Wi-Fi location not available")
    lat, lon = est
    return GeolocateResp(lat=lat, lon=lon, method="WiFi")


@app.get("/mock", response_model=GeolocateResp)
def geolocate_mock():
    lat, lon, method = generate_mock_location()
    return GeolocateResp(lat=lat, lon=lon, method=method)
