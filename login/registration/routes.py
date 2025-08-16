# registration/routes.py
from flask import Blueprint, request, jsonify, render_template
import logging
import base64
import uuid
import json
import time
from datetime import datetime, timezone
import os, sys, boto3
from boto3.dynamodb.conditions import Key, Attr
# pairing_token.py を一階層上に見にいく
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from registration.pairing_token import create_pairing_token, save_pairing_token
from auth_py.fingerprint       import normalize_fp
from auth_py.app_auth          import hash_password_interface as _hash_pw_
from registration.config       import AWS_REGION, DEVICES_TABLE, PAIRING_TOKEN_TABLE

# DynamoDB テーブル
dynamodb                = boto3.resource("dynamodb", region_name=AWS_REGION)
pairing_tokens_table    = dynamodb.Table(PAIRING_TOKEN_TABLE)
users_table             = dynamodb.Table("UsersTable")

# ロガー設定（そのまま）
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s'))
logger.addHandler(handler)

registration_bp = Blueprint("registration_bp", __name__, template_folder="templates")
auth_bp = Blueprint("auth_bp", __name__)


@registration_bp.route("/", methods=["GET", "POST"], strict_slashes=False)
def registration_index():
    if request.method == "POST":
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json()
        else:
            data = request.form.to_dict()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        try:
            from registration.app_registration import register_user_interface
            result = register_user_interface(data)
            return jsonify(result), 200
        except Exception as e:
            import traceback; traceback.print_exc()
            logger.error("登録失敗: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
    return render_template("register.html")


@registration_bp.route("/revoke_cert", methods=["POST"])
def revoke_cert():
    data = request.get_json(silent=True) or {}
    user_uuid = data.get("uuid")
    if not user_uuid:
        return jsonify({"error": "uuid is required"}), 400

    try:
        now = datetime.now(timezone.utc).isoformat()
        users_table.update_item(
            Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
            UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
            ExpressionAttributeValues={":r": True, ":t": now}
        )
        return jsonify({"success": True, "revoked_at": now}), 200
    except Exception as e:
        logger.error("証明書失効エラー: %s", e)
        return jsonify({"error": "revoke failed", "detail": str(e)}), 500


@registration_bp.route("/pairing_token", methods=["POST"])
def request_pairing_token():
    """
    端末追加時のエンドポイント。
    username/password(+client_cert_fp)を検証して、device_tokenを返す。
    """
    data = request.get_json(silent=True) or {}
    username       = data.get("username")
    password       = data.get("password")
    client_cert_fp = normalize_fp(data.get("client_cert_fp", ""))

    if not all([username, password]):
        return jsonify({"error": "username and password are required"}), 400

    # ① username で全行取得（件数はごく少ないので scan で可）
    # --------- eventual‑consistency 対策 ----------
    user = None
    for _ in range(6):          # 最大 ≒1.5 秒待つ
        resp   = users_table.scan(
            FilterExpression=Attr("username").eq(username)
        )
        items  = resp.get("Items", [])
        if items:
            user = items[0]     # どちらの行でもパスワードは同じ
            break
        time.sleep(0.25)

    if user is None:
        return jsonify({"error": "user not found"}), 404

    # --- パスワード検証
    salt = bytes.fromhex(user["salt"])
    if _hash_pw_(password, salt) != user["password_hash"]:
        return jsonify({"error": "password mismatch"}), 401

    # --- フィンガープリント検証（あれば）
    if client_cert_fp:
        devices_table = dynamodb.Table(DEVICES_TABLE)
        dev_resp = devices_table.scan(
            FilterExpression="#u = :u AND #f = :f",
            ExpressionAttributeNames={"#u": "uuid", "#f": "fingerprint"},
            ExpressionAttributeValues={":u": user["uuid"], ":f": client_cert_fp},
            ConsistentRead=True
        )
        if not dev_resp.get("Items"):
            return jsonify({"error": "unregistered device"}), 403

    # --- トークン発行＆保存（create_pairing_token内でDynamoDBに書き込み）
    ttl = 600  # 有効期限（秒）
    token = create_pairing_token(user["uuid"], ttl)
    expires_at = int(time.time()) + ttl

    return jsonify({
        "device_token": token,
        "uuid":         user["uuid"],
        "expires_at":   expires_at
    }), 200


@auth_bp.route("/user/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "message": "username/password required"}), 400

    # usernameでユーザー検索（GSIがなければscan）
    resp = users_table.scan(
        FilterExpression=Attr("username").eq(username)
    )
    items = resp.get("Items", [])
    if not items:
        return jsonify({"success": False, "message": "user not found"}), 404
    user = items[0]

    # パスワード検証
    salt = bytes.fromhex(user["salt"])
    if _hash_pw_(password, salt) != user["password_hash"]:
        return jsonify({"success": False, "message": "invalid credentials"}), 401

    # 証明書＋鍵の返却
    return jsonify({
        "success":                 True,
        "clientCertificatePem":    user["certificate"]["pem"],
        "ntruPrivateKeyPem":       user.get("ntru_private_key"),
        "dilithiumPrivateKeyPem":  user.get("dilithium_private_key"),
        "rsaPrivateKey":           user.get("rsa_private_key"),
        "message":                 "login successful"
    }), 200