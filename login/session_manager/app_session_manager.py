# session_manager/app_session_manager.py

"""
app_session_manager.py

Flaskアプリとしてセッション管理の各機能をAPI化し、
localhost:5001 で起動できるようにする。

エンドポイント例:
- POST /session/create            -> 新規セッション作成
- POST /session/record_login      -> ログイン記録の保存
- GET  /session/retrieve?user_uuid=xxx    -> ユーザーセッション一覧取得
- POST /session/extend            -> セッション延長
- POST /session/purge             -> 古いセッション削除
- GET  /session/analyze?user_uuid=xxx     -> セッション分析結果
- GET  /session/jwt               -> JWTトークン中身確認 (HTML)
"""

import sys
import os
import logging

from flask import Flask, Blueprint, request, jsonify, render_template
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from session_manager.session_service import (
    create_session, retrieve_user_sessions, extend_session, purge_sessions
)
from session_manager.session_manager import record_login
from session_manager.session_analysis import analyze_sessions
from session_manager.create_login_table import create_login_history_table

# --- device_manager が存在しない場合のスタブ定義 ---
try:
    from device_manager.app_device_manager import (
        register_device_interface,
        handle_concurrency_interface
    )
except ImportError:
    def register_device_interface(*args, **kwargs):
        return {}
    def handle_concurrency_interface(*args, **kwargs):
        return None

# ログ設定: コンソール出力
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprint: templates は session_manager/templates に配置
session_bp = Blueprint(
    "session_bp",
    __name__,
    template_folder="templates",
)

@session_bp.route("/create", methods=["POST"])
def create_session_endpoint():
    """
    POST /session/create
    JSON例:
    {
      "user_uuid": "...",
      "ip_address": "127.0.0.1",
      "device_name": "MyPC",
      "qr_code": "..."
    }
    """
    data = request.get_json() or {}
    user_uuid   = data.get("user_uuid")
    ip_address  = data.get("ip_address", "127.0.0.1")
    device_name = data.get("device_name", "SessionDevice")
    qr_code     = data.get("qr_code", "")

    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    # 1) セッション作成
    sess_info = create_session(user_uuid, ip_address)

    # 2) デバイス管理 + 並行制御
    try:
        new_device = register_device_interface(
            user_uuid=user_uuid,
            qr_code=qr_code,
            device_name=device_name
        )
        handle_concurrency_interface(user_uuid, new_device.get("device_id"))
    except Exception as e:
        logger.error("端末登録 or concurrencyエラー: %s", e)

    return jsonify(sess_info), 200

@session_bp.route("/record_login", methods=["POST"])
def record_login_endpoint():
    """
    POST /session/record_login
    JSON: { "user_uuid": "xxx", "ip_address": "127.0.0.1" }
    """
    data = request.get_json() or {}
    user_uuid  = data.get("user_uuid")
    ip_address = data.get("ip_address", "127.0.0.1")
    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    record_login(user_uuid, ip_address)
    return jsonify({"message": "login record saved"}), 200

@session_bp.route("/retrieve", methods=["GET"])
def retrieve_sessions_endpoint():
    """
    GET /session/retrieve?user_uuid=xxx
    """
    user_uuid = request.args.get("user_uuid")
    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    sessions = retrieve_user_sessions(user_uuid)
    return jsonify(sessions), 200

@session_bp.route("/extend", methods=["POST"])
def extend_session_endpoint():
    """
    POST /session/extend
    JSON: {
      "user_uuid": "...",
      "session_id": "...",
      "additional_minutes": 30
    }
    """
    data = request.get_json() or {}
    user_uuid          = data.get("user_uuid")
    session_id         = data.get("session_id")
    additional_minutes = data.get("additional_minutes", 30)

    if not user_uuid or not session_id:
        return jsonify({"error": "user_uuid and session_id are required"}), 400

    result = extend_session(user_uuid, session_id, additional_minutes)
    return jsonify(result), 200

@session_bp.route("/purge", methods=["POST"])
def purge_sessions_endpoint():
    """
    POST /session/purge
    JSON: { "retention_days": 1 }
    """
    data           = request.get_json() or {}
    retention_days = data.get("retention_days", 1)
    purge_sessions(retention_days)
    return jsonify({"message": "old sessions purged"}), 200

@session_bp.route("/analyze", methods=["GET"])
def analyze_endpoint():
    """
    GET /session/analyze?user_uuid=xxx
    """
    user_uuid = request.args.get("user_uuid")
    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    analysis = analyze_sessions(user_uuid)
    return jsonify(analysis), 200

@session_bp.route("/jwt", methods=["GET"])
def jwt_status():
    """
    GET /session/jwt
    JWTトークンの中身を確認するHTMLを返す
    """
    return render_template("jwt.html")

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.register_blueprint(session_bp, url_prefix="/session")
    create_login_history_table()
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=False)
