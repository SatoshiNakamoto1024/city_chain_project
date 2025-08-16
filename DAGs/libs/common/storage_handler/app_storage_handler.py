# city_chain_project\network\DAGs\common\storage_handler\app_storage_handler.py
"""
app_storage_handler.py
======================
FastAPI を使って StorageHandler を HTTP API 化。

Endpoints:
  GET  /has_space?device_type={device_type}&size={size}
     → {"device_type": str, "size": int, "has_space": bool}
  POST /save
     JSON body: {
       "device_type": str,
       "name": str,
       "data": str  # base64-encoded bytes
     }
     → {"saved": bool}

起動例:
    python -m network.DAGs.common.storage_handler.app_storage_handler
"""
from __future__ import annotations
import base64
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.manager import StorageManager

app = FastAPI(title="Storage Handler Service")


class SaveRequest(BaseModel):
    device_type: str
    name: str
    data: str  # base64-encoded payload


@app.get("/has_space")
async def has_space(
    device_type: str = Query(..., description="android|ios|iot|game"),
    size: int = Query(..., ge=0, description="requested fragment size in bytes"),
):
    handler = StorageManager.get_handler(device_type)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unsupported device_type: {device_type}")
    ok = handler.has_space(size)
    return {"device_type": device_type, "size": size, "has_space": ok}


@app.post("/save")
async def save_fragment(req: SaveRequest):
    handler = StorageManager.get_handler(req.device_type)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unsupported device_type: {req.device_type}")
    try:
        payload = base64.b64decode(req.data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in 'data'")
    saved = handler.save_fragment(req.name, payload)
    return {"saved": saved}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8083,
        log_level="info",
    )
