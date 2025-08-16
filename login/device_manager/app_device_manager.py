# device_manager/app_device_manager.py
"""
app_device_manager.py

複数端末を扱うための Flaskアプリ(またはBlueprint)。
- /device/register     : 端末を新しくユーザーに紐付け（2台目,3台目など）
- /device/list         : ユーザーの登録端末一覧
- /device/unbind       : 特定端末の登録解除
- /device/force_logout : 同時利用端末が1台のみの場合、既存端末を強制ログアウト
  (実運用では session_manager 連携などでログアウトさせる)

※ 本実装では、ユーザー基本情報はUsersTableで管理し、追加端末情報はDevicesTableに保存するように下位層を修正済みとする。
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import logging
from flask import Flask, Blueprint, request, jsonify

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

device_bp = Blueprint("device_bp", __name__)

# 下位層の device_service の関数をインターフェースとして利用
from device_manager.device_service import (
    register_device_for_user as _register_device_for_user,
    list_devices_for_user   as _list_devices_for_user,
    unbind_device           as _unbind_device,
    force_logout_other_devices as _force_logout_other_devices
)
from device_manager.concurrency_policy import (
    handle_concurrency_if_needed as _handle_concurrency_if_needed
)

# 公開インターフェース関数
def register_device_interface(user_uuid: str, qr_code: str, device_name: str, force: bool = False) -> dict:
    return _register_device_for_user(user_uuid, qr_code, device_name, force)

def list_devices_interface(user_uuid: str) -> list:
    return _list_devices_for_user(user_uuid)

def unbind_device_interface(user_uuid: str, device_id: str):
    _unbind_device(user_uuid, device_id)

def force_logout_interface(user_uuid: str, new_device_id: str) -> dict:
    return _force_logout_other_devices(user_uuid, new_device_id)

def handle_concurrency_interface(user_uuid: str, new_device_id: str):
    return _handle_concurrency_if_needed(user_uuid, new_device_id)


@device_bp.route("/register", methods=["POST"])
def register_device_endpoint():
    """
    POST /device/register
    JSON例:
    {
      "user_uuid": "user-abc123",
      "qr_code": "xxxxx",
      "device_name": "MySecondDevice",
      "force": true  ← 強制ログアウトモード（デフォルトはfalse）
    }
    """
    data = request.get_json() or {}
    user_uuid   = data.get("user_uuid")
    qr_code     = data.get("qr_code", "")
    device_name = data.get("device_name", f"Device_{uuid.uuid4().hex[:5]}")
    force       = bool(data.get("force", False))

    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    try:
        new_device = _register_device_for_user(user_uuid, qr_code, device_name, force)
        # 並行制御も呼び出す（必要に応じて）
        _handle_concurrency_if_needed(user_uuid, new_device["device_id"])
        return jsonify(new_device), 200
    except Exception as e:
        msg = str(e)
        logger.warning("端末登録拒否: %s", msg)
        # "ログイン中" という日本語メッセージを例に409を返す
        status = 409 if "ログイン中" in msg else 500
        return jsonify({"error": msg}), status

@device_bp.route("/list", methods=["GET"])
def list_device_endpoint():
    """
    GET /device/list?user_uuid=xxx
    """
    user_uuid = request.args.get("user_uuid")
    if not user_uuid:
        return jsonify({"error": "user_uuid is required"}), 400

    try:
        devices = list_devices_interface(user_uuid)
        return jsonify(devices), 200
    except Exception as e:
        logger.error("端末一覧取得エラー: %s", e)
        return jsonify({"error": str(e)}), 500

@device_bp.route("/unbind", methods=["POST"])
def unbind_device_endpoint():
    """
    POST /device/unbind
    JSON: { "user_uuid": "...", "device_id": "..." }
    """
    data = request.get_json() or {}
    user_uuid = data.get("user_uuid")
    device_id = data.get("device_id")
    if not user_uuid or not device_id:
        return jsonify({"error": "user_uuid and device_id are required"}), 400

    try:
        unbind_device_interface(user_uuid, device_id)
        return jsonify({"message": "Device unbound"}), 200
    except Exception as e:
        logger.error("端末解除エラー: %s", e)
        return jsonify({"error": str(e)}), 500

@device_bp.route("/force_logout", methods=["POST"])
def force_logout_endpoint():
    """
    POST /device/force_logout
    JSON: { "user_uuid": "...", "new_device_id": "..." }
    → 同時利用数1台ポリシーの場合、新規端末以外を強制ログアウトする
    """
    data = request.get_json() or {}
    user_uuid     = data.get("user_uuid")
    new_device_id = data.get("new_device_id")
    if not user_uuid or not new_device_id:
        return jsonify({"error": "user_uuid and new_device_id are required"}), 400

    try:
        result = force_logout_interface(user_uuid, new_device_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error("強制ログアウトエラー: %s", e)
        return jsonify({"error": str(e)}), 500

def create_app():
    app = Flask(__name__)
    app.register_blueprint(device_bp, url_prefix="/device")
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
