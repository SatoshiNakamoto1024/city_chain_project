# login_app/login.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, render_template, jsonify
import logging
import boto3
import hashlib
from login_app.config import AWS_REGION, USER_TABLE

# device_manager の端末登録機能を利用
from device_manager.app_device_manager import register_device_interface

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

login_bp = Blueprint("login_bp", __name__, template_folder="templates")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USER_TABLE)

@login_bp.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")

@login_bp.route("/", methods=["POST"])
def login_api():
    data = request.get_json() if request.is_json else request.form.to_dict()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    username = data.get("username")
    password = data.get("password")
    device_name = data.get("device_name", "MyDevice")
    qr_code = data.get("qr_code", "")
    force = data.get("force", False)

    if not username or not password:
        return jsonify({"success": False, "error": "username and password are required"}), 400

    try:
        # ユーザーを検索（本来は適切なインデックスを利用）
        response = users_table.scan()
        items = response.get("Items", [])
        found_item = None
        for it in items:
            if it.get("username") == username or it.get("email") == username:
                found_item = it
                break

        if not found_item:
            return jsonify({"success": False, "error": "ユーザーが見つかりません"}), 401

        salt = found_item.get("salt")
        stored_hash = found_item.get("password_hash")
        input_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        if input_hash != stored_hash:
            return jsonify({"success": False, "error": "パスワードが不一致"}), 401

        # 登録済みのクライアント証明書フィンガープリントはDBから読み出す
        # （ユーザーの端末登録は、登録時にQRコードなどで行われ、DBに保存済みとする）
        user_uuid = found_item["uuid"]

        # device_manager による端末登録（2台目の場合はQRコードも利用）
        new_device = register_device_interface(
            user_uuid=user_uuid,
            qr_code=qr_code,
            device_name=device_name,
            force=force
        )

        # JWT発行
        import jwt
        from datetime import datetime, timedelta
        JWT_SECRET = "my_jwt_secret_2025"
        JWT_ALGORITHM = "HS256"
        payload = {
            "user_uuid": user_uuid,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        logger.info("ログイン成功: %s (uuid=%s), device_id=%s", username, user_uuid, new_device.get("device_id"))
        return jsonify({
            "success": True,
            "jwt_token": token,
            "user_uuid": user_uuid,
            "device_info": new_device
        })

    except Exception as e:
        logger.error("ログインエラー: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
