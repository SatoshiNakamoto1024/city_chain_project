# municipality_verification/municipality_login.py

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import hmac
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template
import jwt
import logging
import boto3
from boto3.dynamodb.conditions import Key
from municipality_verification.config import (
    ADMIN_TABLE,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    AWS_REGION
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprintの作成。フラスクアプリ本体(app.py)でこのBlueprintを登録して使います
admin_login_bp = Blueprint("admin_login", __name__, template_folder="../../templates")

# AWS DynamoDB接続
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
admin_table = dynamodb.Table(ADMIN_TABLE)

def hash_password(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def generate_admin_jwt(admin_id):
    payload = {
        "admin_id": admin_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

@admin_login_bp.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    """
    /admin_login ルート。
    GET → admin_login.html (ログインフォーム) を返す
    POST → JSON または form で受け取り、DynamoDB から認証
    """
    if request.method == "GET":
        # ログインフォームのHTMLを返す
        return render_template("admin_login.html")

    elif request.method == "POST":
        # ログインフォームの送信内容を受け取って認証
        data = request.get_json() if request.is_json else request.form.to_dict()
        admin_id = data.get("admin_id")
        password = data.get("password")
        municipality = data.get("municipality")  # 必要なら

        if not admin_id or not password or not municipality:
            return jsonify({"error": "admin_id, password, および municipality は必須です"}), 400

        try:
            # DynamoDBに複合キー(admin_id, municipality) で問い合わせ
            response = admin_table.get_item(Key={"admin_id": admin_id, "municipality": municipality})
            if "Item" not in response:
                return jsonify({"error": "職員が存在しません"}), 401

            admin = response["Item"]
            stored_hash = admin["password_hash"]
            salt = admin["salt"]

            input_hash = hash_password(password, salt)

            if not hmac.compare_digest(stored_hash, input_hash):
                return jsonify({"error": "パスワードが一致しません"}), 401

            token = generate_admin_jwt(admin_id)
            return jsonify({"success": True, "admin_jwt": token, "admin_id": admin_id})

        except Exception as e:
            logger.error("DynamoDBエラー: %s", e)
            return jsonify({"error": f"認証中にエラーが発生しました: {e}"}), 500
