# File: user_manager/utils/check_storage_middleware.py
from flask import Blueprint, request, jsonify, redirect, url_for
from user_manager.utils.platform_utils import detect_platform_from_headers
from user_manager.utils.storage_checker import check_storage

check_storage_bp = Blueprint("check_storage", __name__)

@check_storage_bp.route("/prelogin", methods=["POST"])
def pre_login_check():
    """
    ログイン前のストレージチェック処理
    クライアント情報に応じて100MBの空きがあるか確認し、
    OKなら login_app へ処理を渡す（ここでは 200 返すだけでよい）
    """
    headers = request.headers
    platform_type = detect_platform_from_headers(headers)

    # Android/iOS/TVなどはクライアントから送信された空き容量を使用
    client_free_space = request.json.get("client_free_space", 0)
    if platform_type in ["android", "ios", "game", "tv", "car"]:
        if client_free_space < 100 * 1024 * 1024:
            return jsonify({"success": False, "message": "Insufficient client storage"}), 403
        else:
            return jsonify({"success": True, "message": "Prelogin check passed"}), 200

    # PCやIoTなどはサーバーのdiskを確認
    if not check_storage(platform_type):
        return jsonify({"success": False, "message": "Server storage insufficient"}), 403

    return jsonify({"success": True, "message": "Prelogin check passed"}), 200
