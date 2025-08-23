# D:\city_chain_project\network\DAGs\common\errors\app_errors.py
"""
app_errors.py ─ 共通エラー基盤デモ FastAPI

起動例:
    PYTHONPATH=./network/DAGs/common uvicorn errors.app_errors:app --reload
"""
from __future__ import annotations

import asyncio
from typing import Dict

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

# ───────────────────────────────────────────────
# 共通エラー基盤
# ───────────────────────────────────────────────
from errors import (
    BaseError,
    NetworkError,
    StorageError,
    ValidationError,
    handle,  # デコレータ: ポリシー＋リトライ
)

app = FastAPI(title="Common-Errors Demo")

# --------------------------------------------------------------------------
# 例外 → HTTP レスポンス
# --------------------------------------------------------------------------


@app.exception_handler(BaseError)
async def base_err_handler(_: Request, exc: BaseError) -> JSONResponse:
    """
    独自例外を共通 JSON 形式に変換
    * ValidationError → 400
    * それ以外        → 500
    """
    status = 400 if isinstance(exc, ValidationError) else 500
    return JSONResponse(
        status_code=status,
        content={"error": exc.__class__.__name__, "message": str(exc)},
    )


# --------------------------------------------------------------------------
# 疑似バックエンド（リトライ対象）
# --------------------------------------------------------------------------

_attempts: Dict[str, int] = {}  # 失敗回数トラッキング


@handle
def flaky_storage(key: str, max_fail: int) -> None:
    """max_fail 回 StorageError を投げた後に成功する同期関数"""
    cur = _attempts.get(key, 0)
    if cur < max_fail:
        _attempts[key] = cur + 1
        raise StorageError(f"simulated fail {cur + 1}/{max_fail}")
    _attempts.pop(key, None)


@handle
async def flaky_network_async(key: str, max_fail: int) -> None:
    """非同期版 NetworkError"""
    cur = _attempts.get(key, 0)
    if cur < max_fail:
        _attempts[key] = cur + 1
        raise NetworkError(f"simulated net-fail {cur + 1}/{max_fail}")
    _attempts.pop(key, None)
    await asyncio.sleep(0.01)


# --------------------------------------------------------------------------
# エンドポイント
# --------------------------------------------------------------------------


@app.get("/storage_flaky")
def storage_flaky(
    key: str = Query(...),
    fails: int = Query(..., ge=0, le=10),
):
    """
    `fails` 回連続で StorageError を発生 → リトライで回復すれば OK.
    リトライ上限を超えると 500 + {"error":"StorageError"}
    """
    _attempts.pop(key, None)  # カウンタ初期化
    try:
        flaky_storage(key, fails)
        return {"result": "ok"}
    except StorageError as exc:
        # ここに来るのはリトライ上限を超えたときだけ
        return JSONResponse(
            status_code=500,
            content={"error": "StorageError", "message": str(exc)},
        )


@app.get("/network_flaky")
async def network_flaky(
    key: str = Query(...),
    fails: int = Query(..., ge=0, le=10),
):
    """
    非同期 NetworkError デモ。
    失敗時は 500 + {"error":"NetworkError"}
    """
    _attempts.pop(key, None)
    try:
        await flaky_network_async(key, fails)
        return {"result": "pong"}
    except NetworkError as exc:
        return JSONResponse(
            status_code=500,
            content={"error": "NetworkError", "message": str(exc)},
        )


@app.get("/validate")
def validate(q: int | None = None):
    """クエリ `q` が必須。欠落すると ValidationError → 400."""
    if q is None:
        raise ValidationError("query param 'q' is required")
    return {"q": q}


# --------------------------------------------------------------------------
# スクリプト実行用
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
