# login_app/login_routes.py
"""
login_routes.py  – フェーズ2 本番仕様
 - challenge/verify でも fingerprint を必須チェック
"""

import sys, os, logging, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
from typing import Dict, Any
from login_app.config import USERS_TABLE, AWS_REGION
import boto3 as _b3
from boto3.dynamodb.conditions import Key, Attr
import jwt
from flask import Blueprint, request, jsonify, render_template

from wallet.wallet_service import get_wallet_by_user
from login_app.config import JWT_SECRET
from login_app.cert_checker import verify_certificate          # ←  失効 & FP 照合
from login_app.login_service import (
    get_user_by_login,
    get_user_by_uuid,
    verify_password,
)
from device_manager.app_device_manager import register_device_interface
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ntru", "dilithium-py")))
from app_dilithium import verify_message                        # PyO3‑wrap

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

login_bp = Blueprint("login_bp", __name__, template_folder="templates")

# ────────────── チャレンジ保持 ──────────────
login_challenges: Dict[str, str] = {}
# ───────────────────────────────────────────


# --------------------------------------------------------------------------
@login_bp.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")


# --------------------------------------------------------------------------
# ① /login/challenge  ― fingerprint も必須
# --------------------------------------------------------------------------
@login_bp.route("/challenge", methods=["POST"])
def login_challenge():
    """
    JSON : {
        "username" | "uuid" ,
        "password",
        "client_cert_fp"      ← 必須
    }
    """
    data = request.get_json(silent=True) or {}
    user_id     = data.get("username") or data.get("uuid")
    password    = data.get("password")
    cert_fp_raw = data.get("client_cert_fp")

    if not (user_id and password and cert_fp_raw):
        return jsonify({"error": "username/uuid, password, client_cert_fp are required"}), 400

    # ── ユーザー取得 & PW 検証 ──────────────────
    user = get_user_by_login(user_id) if data.get("username") else get_user_by_uuid(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    if not verify_password(password, user):
        return jsonify({"error": "invalid password"}), 401
    # 1) ここで uuid と user の有無を出す
    logger.info("DEBUG login_challenge: user_id=%s  -> user=%s", user_id, bool(user))

    # ── FP 照合（失効含むオンラインチェック） ─────────
    try:
        verify_certificate(user, user["certificate"]["client_cert"])   # DB 保存済み PEM を使う
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    # OK → チャレンジ発行
    challenge = os.urandom(32).hex()
    login_challenges[user["uuid"]] = challenge
    logger.info("challenge issued uuid=%s", user["uuid"])
    return jsonify({"challenge": challenge}), 200


# --------------------------------------------------------------------------
# ② /login/verify  – (署名 + 失効チェック)
# --------------------------------------------------------------------------
@login_bp.route("/verify", methods=["POST"])
def login_verify():
    """
    JSON : { "user_uuid": "...", "signature": "<Base64>" }
    """
    data          = request.get_json(silent=True) or {}
    user_uuid     = data.get("user_uuid")
    signature_b64 = data.get("signature")

    if not user_uuid or not signature_b64:
        return jsonify({"error": "user_uuid and signature are required"}), 400

    challenge_hex = login_challenges.get(user_uuid)
    if not challenge_hex:
        return jsonify({"error": "challenge not found or expired"}), 400

    # ── ユーザー&証明書有効性確認 ──────────────────
    user = get_user_by_uuid(user_uuid)
    if not user:
        return jsonify({"error": "user not found"}), 404
    if user["certificate"].get("revoked"):
        return jsonify({"error": "certificate revoked"}), 403

    try:
        verify_certificate(user, user["certificate"]["client_cert"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    
    # ── 署名検証 (Dilithium) ───────────────────────
    try:
        sig_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        return jsonify({"error": f"invalid signature (base64): {e}"}), 400
    msg_bytes = bytes.fromhex(challenge_hex)

    # 公開鍵の bytes 抽出
    pk_raw = user["dilithium_public_key"]
    pub_bytes = (
        bytes(pk_raw) if isinstance(pk_raw, list)
        else pk_raw if isinstance(pk_raw, (bytes, bytearray))
        else (bytes.fromhex(pk_raw) if len(pk_raw) % 2 == 0 else base64.b64decode(pk_raw))
    )

    if not verify_message(msg_bytes, sig_bytes, pub_bytes):
        return jsonify({"error": "signature verification failed"}), 401

    # ── JWT 発行 ──────────────────────────────────
    token = jwt.encode(
        {"uuid": user_uuid, "role": "resident", "exp": datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET,
        algorithm="HS256"
    )
    login_challenges.pop(user_uuid, None)
    logger.info("login verified uuid=%s", user_uuid)
    return jsonify({"jwt_token": token}), 200


# --------------------------------------------------------------------------
# ③ /login  (1‑step)  – 変更無し（fingerprint は verify_certificate 内）
# --------------------------------------------------------------------------
@login_bp.route("/", methods=["POST"])
def login_handler():
    data: Dict[str, Any] = request.get_json(silent=True) or request.form.to_dict() or {}

    username  = data.get("username")
    password  = data.get("password")
    cert_b64  = data.get("client_cert")
    device_nm = data.get("device_name", "MyDevice")
    qr_code   = data.get("qr_code", "")
    force     = bool(data.get("force"))

    if not (username and password and cert_b64):
        return jsonify({"success": False,
                        "error": "username, password and client_cert are required"}), 400

    user_item = get_user_by_login(username)
    if not user_item or not verify_password(password, user_item):
        return jsonify({"success": False, "error": "invalid credentials"}), 401

    try:
        verify_certificate(user_item, cert_b64)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 401
    # 2) ここでも確認（REGISTRATION→USER_PROFILE 行が残っているか）
    logger.info("DEBUG one‑step: username=%s  -> user=%s", username, bool(user_item))
    
    # デバイス登録
    device_info = register_device_interface(
        user_uuid=user_item["uuid"],
        qr_code=qr_code,
        device_name=device_nm,
        force=force,
    )

    token = jwt.encode(
        {"uuid": user_item["uuid"], "role": "resident", "exp": datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET,
        algorithm="HS256"
    )
    
    rows = _b3.resource("dynamodb", region_name=AWS_REGION)\
              .Table(USERS_TABLE)\
              .query(KeyConditionExpression=Key("uuid").eq(user_item["uuid"]),
                     ConsistentRead=True)["Items"]
    logger.info("DEBUG after DeviceManager: rows=%s", rows)
    
    # JWT
    payload = {
        "user_uuid": user_item["uuid"],
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    # ✅ Wallet 情報を取得
    wallet = get_wallet_by_user(user_item["uuid"])

    logger.info("LOGIN OK user=%s uuid=%s device=%s",
                username, user_item["uuid"], device_info.get("device_id"))
    
    return jsonify({
        "success": True,
        "jwt_token": token,
        "user_uuid": user_item["uuid"],
        "device_info": device_info,
        "wallet_address": wallet.wallet_address if wallet else "",
        "balance": float(wallet.balance) if wallet else 0.0
    }), 200