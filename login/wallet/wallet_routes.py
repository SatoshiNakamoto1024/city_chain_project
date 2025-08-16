# login/wallet/wallet_routes.py
"""
REST API エンドポイント /wallet/...
（必要最小限：残高取得と入金/出金）
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
from flask import Blueprint, request, jsonify
from auth_py.jwt_manager import verify_jwt
from wallet.wallet_service import (
    get_wallet_by_user, get_wallet, increment_balance
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

wallet_bp = Blueprint("wallet_bp", __name__, url_prefix="/wallet")

# --- GET /wallet/me  → 自分のウォレット情報 ---
@wallet_bp.route("/me", methods=["GET"])
def wallet_me():
    jwt_token = request.headers.get("Authorization","").replace("Bearer ","").strip()
    payload   = verify_jwt(jwt_token)
    user_uuid = payload.get("uuid") or payload.get("user_uuid")
    w = get_wallet_by_user(user_uuid)
    if not w:
        return jsonify({"error":"wallet not found"}), 404
    return jsonify({
        "wallet_address": w.wallet_address,
        # Decimal を float に変換して返す
        "balance": float(w.balance)
    }), 200

# --- POST /wallet/adjust  {wallet_address, delta} ---
@wallet_bp.route("/adjust", methods=["POST"])
def wallet_adjust():
    data = request.get_json() or {}
    addr  = data.get("wallet_address","")
    delta = float(data.get("delta",0))
    if not addr:
        return jsonify({"error":"wallet_address required"}), 400
    try:
        bal = increment_balance(addr, delta)
        return jsonify({"wallet_address": addr, "balance": bal}), 200
    except Exception as e:
        logger.exception("wallet adjust failed")
        return jsonify({"error": str(e)}), 500
