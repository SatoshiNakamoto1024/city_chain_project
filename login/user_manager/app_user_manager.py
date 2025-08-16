# user_manager/app_user_manager.py

"""
app_user_manager.py

Flaskアプリとしてユーザー関連の各機能
(プロフィール更新, パスワード変更, 鍵更新, lifeform登録など)をAPI化。

※ユーザー登録 (/user/register) は別モジュールで実装済みの想定
"""
import boto3
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
from flask import Flask, Blueprint, request, jsonify

from user_manager.user_service import (
    update_user_profile,
    change_user_password,
    update_user_keys,
    register_lifeform
)

# Blueprint 定義
user_bp = Blueprint("user_bp", __name__)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# DynamoDB 設定
from user_manager.config import AWS_REGION, USERS_TABLE, STORAGE_USAGE_TABLE
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE)
storage_table = dynamodb.Table(STORAGE_USAGE_TABLE)

@user_bp.route("/profile/update", methods=["POST"])
def update_profile_endpoint():
    """
    POST /user/profile/update
    JSON:
    {
      "user_uuid": "...",
      "address": "new address",
      "phone": "09099999999",
      ...
    }
    """
    data = request.get_json() or {}
    user_uuid = data.get("user_uuid")
    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    # user_uuid以外をアップデート用データに抽出
    update_data = {k: v for k, v in data.items() if k != "user_uuid"}
    try:
        updated = update_user_profile(user_uuid, update_data)
        return jsonify(updated), 200
    except Exception as e:
        logger.error("プロフィール更新エラー: %s", e)
        return jsonify({"error": str(e)}), 500

@user_bp.route("/password/change", methods=["POST"])
def change_password_endpoint():
    """
    POST /user/password/change
    JSON:
    {
      "user_uuid": "...",
      "current_password": "xxx",
      "new_password": "yyy"
    }
    """
    data = request.get_json() or {}
    user_uuid        = data.get("user_uuid")
    current_password = data.get("current_password")
    new_password     = data.get("new_password")

    if not all([user_uuid, current_password, new_password]):
        return jsonify({
            "error": "user_uuid, current_password, new_password are required"
        }), 400

    try:
        result = change_user_password(user_uuid, current_password, new_password)
        return jsonify(result), 200
    except Exception as e:
        logger.error("パスワード変更エラー: %s", e)
        return jsonify({"error": str(e)}), 500

@user_bp.route("/keys/update", methods=["POST"])
def update_keys_endpoint():
    """
    POST /user/keys/update
    JSON:
    {
        "user_uuid": "...",
        "rsa_pub_pem": "-----BEGIN PUBLIC KEY-----..."
    }
    """
    data = request.get_json() or {}
    user_uuid    = data.get("user_uuid")
    rsa_pub_pem  = data.get("rsa_pub_pem")

    if not user_uuid or not rsa_pub_pem:
        return jsonify({"error": "user_uuid and rsa_pub_pem are required"}), 400

    try:
        result = update_user_keys(user_uuid, rsa_pub_pem)
        return jsonify(result), 200
    except Exception as e:
        logger.error("鍵更新エラー: %s", e)
        return jsonify({"error": str(e)}), 500
    
@user_bp.route("/lifeform/register", methods=["POST"])
def register_lifeform_endpoint():
    """
    POST /user/lifeform/register
    JSON:
    {
      "user_id": "...",
      "team_name": "...",
      "affiliation": "...",
      "municipality": "...",
      "state": "...",
      "country": "...",
      "extra_dimensions": ["Extra1","Extra2",...]
    }
    """
    data = request.get_json() or {}
    if "user_id" not in data:
        return jsonify({"error": "user_id is required"}), 400

    try:
        record = register_lifeform(data)
        return jsonify(record), 200
    except Exception as e:
        logger.error("生命体登録エラー: %s", e)
        return jsonify({"error": str(e)}), 500

def create_app():
    """
    Flask アプリ生成用ファクトリ関数。
    テストや本番でも同じく create_app() を呼び出して起動します。
    """
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
    app.register_blueprint(user_bp, url_prefix="/user")
    return app


# 以下を __main__ 部分の前に追加
app.register_blueprint(user_bp, url_prefix="/user")

if __name__ == "__main__":
    app = create_app()
    # 本番では debug=False にする
    app.run(host="0.0.0.0", port=5000, debug=False)
