# login_app/register.py
# このファイルは、Web アプリの登録エンドポイント（Blueprint）として機能し、
# 登録リクエストを受け取って registration/registration.py の関数を呼び出します。
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import uuid
import boto3
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
import logging

# 新たに作成した registration モジュールから登録処理をインポート
from registration.registration import register_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprint の定義（このモジュールは /register エンドポイントを担当）
register_bp = Blueprint("register_bp", __name__, template_folder="templates")

@register_bp.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Content-Type により JSON かフォームデータかを判定
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json()
        else:
            data = request.form.to_dict()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        try:
            result = register_user(data)
            return jsonify(result), 200
        except Exception as e:
            logger.error("Registration error: %s", e)
            return jsonify({"error": str(e)}), 500
    else:
        return render_template("register.html")


# この Blueprint をメインアプリに登録するためには、login_app のメインアプリ（例えば app_auth.py など）で
# 以下のようにインポートして登録してください：
#   from login_app.register import register_bp
#   app.register_blueprint(register_bp, url_prefix="/register")
