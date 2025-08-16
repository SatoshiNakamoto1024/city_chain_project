# user_manager/app_user_manager.py
"""
app_user_manager.py

Flaskアプリとしてユーザー関連の各機能(プロフィール更新, パスワード変更, 鍵更新, lifeform登録など)をAPI化。

※ユーザー登録 (/register) は login/registration/registration.py の実装を利用する想定
"""

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
from user_manager.user_db import get_user as _get_user  # 内部関数化して公開インターフェースを作成
from user_manager.password_manager import hash_password as _hash_password
from user_manager.profile.profile import profile_bp
from user_manager.lifeform.lifeform import lifeform_bp

# from infra.logging_setup import configure_logging
# configure_logging()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

user_bp = Blueprint("user_bp", __name__)

# ✅ 外部モジュール向けインターフェース
def get_user_interface(user_uuid: str):
    """
    外部からユーザー情報を取得するためのインターフェース関数。
    app_login などから直接 user_db を参照させないための中継。
    """
    return _get_user(user_uuid)

def hash_password_interface(password: str, salt: bytes) -> str:
    """
    外部からパスワードハッシュを計算するためのインターフェース関数。
    user_manager.password_manager の hash_password を隠蔽。
    """
    return _hash_password(password, salt)

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
    user_uuid = data.get("user_uuid")
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not user_uuid or not current_password or not new_password:
        return jsonify({"error": "user_uuid, current_password, new_password are required"}), 400
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
    JSON: { "user_uuid": "..." }

    => user_service.update_user_keys(user_uuid)
       新たなDillithium鍵を生成してpublic_key更新し、secret_keyを返す
    """
    data = request.get_json() or {}
    user_uuid = data.get("user_uuid")
    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400
    try:
        result = update_user_keys(user_uuid)
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
    app = Flask(__name__)
    # 「/user/profile」や「/user/lifeform」でも使われる blueprint
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(lifeform_bp, url_prefix="/lifeform")
    return app

if __name__ == "__main__":
    # NOTE: /user/register は このファイルでは定義しない → login/registration/registration.py で実装
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
