# user_manager/profile/app_profile.py

#!/usr/bin/env python
"""
app_profile.py

プロフィール機能を提供する Flaskアプリ。
localhost:5000/profile で以下の処理を行う:

GET /profile?uuid=xxx
  -> 指定されたユーザーuuidのプロフィールを表示 (profile.html),
     見つからなければ 404 JSONを返す

POST /profile
  -> フォームデータで "uuid" と更新項目を受け取り、DynamoDBを更新。
     結果をJSONで返す
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging
from datetime import datetime
from flask import Flask, Blueprint, request, render_template, jsonify

from user_manager.user_manager import get_user, update_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

profile_bp = Blueprint("profile_bp", __name__, template_folder="templates")

@profile_bp.route("/", methods=["GET", "POST"])
def profile_index():
    if request.method == "POST":
        # フォーム (multipart/form-data or application/x-www-form-urlencoded) を想定
        uuid_val = request.form.get("uuid")
        if not uuid_val:
            return jsonify({"error": "uuid is required"}), 400

        update_data = dict(request.form)
        try:
            update_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            updated_user = update_user(uuid_val, update_data)
            return jsonify(updated_user.to_dict()), 200
        except Exception as e:
            logger.error("プロフィール更新エラー: %s", e)
            return jsonify({"error": str(e)}), 500

    else:
        uuid_val = request.args.get("uuid")
        if not uuid_val:
            return jsonify({"error": "uuid parameter is required"}), 400
        try:
            user = get_user(uuid_val)
        except Exception as e:
            logger.error("get_user エラー: %s", e)
            return jsonify({"error": "User not found"}), 404
        
        if user:
            # テンプレートに user情報を渡して表示
            return render_template("profile.html", user=user.to_dict())
        else:
            return jsonify({"error": "User not found"}), 404

def create_app():
    """
    Blueprintを登録し、Flaskアプリを返す
    """
    app = Flask(__name__)
    app.register_blueprint(profile_bp, url_prefix="/profile")
    return app

if __name__ == "__main__":
    """
    python app_profile.py で直接起動
    """
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
