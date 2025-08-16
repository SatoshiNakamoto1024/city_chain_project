# municipality_verification/municipality_login.py

"""
市町村職員 (staff) ログイン Blueprint
"""
from __future__ import annotations
import os
import sys
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template
import jwt
import boto3

# 親ディレクトリをパスに追加して、config.py 等を import 可能にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from municipality_verification.config import (
    STAFF_TABLE,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    AWS_REGION,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprint 名称：staff_login。テンプレートは ../templates 以下を参照
staff_login_bp = Blueprint(
    "staff_login",
    __name__,
    template_folder="../templates"
)

dynamodb    = boto3.resource("dynamodb", region_name=AWS_REGION)
staff_table = dynamodb.Table(STAFF_TABLE)


# ----------------- ユーティリティ ----------------- #
def _hash_pw(pw: str, salt: str) -> str:
    """
    salt + pw を SHA-256 でハッシュし、16進文字列で返す。
    """
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()


def _make_jwt(staff_id: str) -> str:
    """
    スタッフID入りの JWT を生成して返す。
    """
    payload = {
        "uuid": staff_id,
        "role":   "staff",  
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ----------------- ルート ----------------- #

@staff_login_bp.route("/login", methods=["GET", "POST"])
def staff_login():
    """
    GET  /staff/login : ログインフォーム HTML (staff_login.html) を返す
    POST /staff/login : JSON で {staff_id, password, municipality} を受け取り、
                         検証に成功したら {"success":True, "jwt": "..."} を返す。
                         失敗なら {"success":False, "message": "..."} を返し、HTTP 401 を返す。
    """
    if request.method == "GET":
        # staff_login.html を返す
        return render_template("staff_login.html")

    # POST 処理
    data = request.get_json() if request.is_json else request.form.to_dict()
    staff_id     = data.get("staff_id")
    password     = data.get("password")
    municipality = data.get("municipality")   # テストでは必ず渡ってくる想定

    if not (staff_id and password and municipality):
        return jsonify({"success": False, "message": "staff_id, password, municipality が必須です"}), 400

    try:
        # DynamoDB から該当職員レコードを取得
        resp = staff_table.get_item(Key={"staff_id": staff_id, "municipality": municipality})
        itm = resp.get("Item")
        if not itm:
            return jsonify({"success": False, "message": "職員が存在しません"}), 401

        # パスワードをハッシュ比較
        if not hmac.compare_digest(itm["password_hash"], _hash_pw(password, itm["salt"])):
            return jsonify({"success": False, "message": "パスワード不一致"}), 401

        # 認証成功 → JWT 発行
        token = _make_jwt(staff_id)
        return jsonify({"success": True, "jwt": token})
    except Exception as e:
        logger.exception("DynamoDB error")
        return jsonify({"success": False, "message": f"DynamoDB error: {e}"}), 500
