# File: login/user_manager/utils/login_handler.py

import sys
import os
import logging
from flask import Flask
from flask import Blueprint, request, jsonify

# ルートディレクトリをパスに追加してパッケージを解決
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from user_manager.utils.platform_utils    import detect_platform_from_headers
from user_manager.utils.storage_checker   import check_server_disk_usage
from auth_py.login                        import login_user as real_login

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprint 名・URL プレフィックスを定義
device_auth_bp = Blueprint(
    'device_auth',          # Blueprint の内部識別名
    __name__,
    url_prefix='/device_auth'
)


@device_auth_bp.route("/login", methods=["POST"])
def device_login():
    """
    POST /device_auth/login

    デバイス向け拡張認証エンドポイント。
    1) HTTP ヘッダから platform_type を判定 (pc / iot / android / ios / etc.)
    2) PC/IoT ならサーバー側ディスク空き容量チェック、
       それ以外のデバイスは client_free_space パラメータでチェック（100MB 以上必須）
    3) auth_py.login.login_user() を呼び出して本番認証
    """
    # 1) プラットフォーム判定
    headers   = request.headers
    platform  = detect_platform_from_headers(headers)
    logger.info("Device login start — platform=%s", platform)

    # 2) JSON ボディ取得
    payload   = request.get_json(silent=True) or {}
    username  = payload.get("username", "")
    password  = payload.get("password", "")
    client_fp = payload.get("client_cert_fp", "")

    # 3) クライアント側空き容量 (Android など)
    client_free = 0
    if "client_free_space" in payload:
        try:
            client_free = int(payload["client_free_space"])
        except (TypeError, ValueError):
            client_free = 0

    logger.info(
        "Device login request — user=%s free_space=%s", 
        username, client_free
    )

    # 4) ストレージ判定
    if platform in ("pc", "iot"):
        # サーバー自身のディスク空き容量をチェック
        if not check_server_disk_usage("/"):
            logger.warning("Insufficient server disk space")
            return jsonify({
                "success": False,
                "message": "Not enough server space"
            }), 403
    else:
        # Android/iOS/Game/TV/Car などは client_free_space をチェック
        if client_free < 100 * 1024 * 1024:
            logger.warning("Insufficient client storage: %s bytes", client_free)
            return jsonify({
                "success": False,
                "message": "Insufficient client storage"
            }), 403

    # 5) 本番認証呼び出し
    try:
        # real_login は {'success': True, 'jwt_token': str, 'uuid': str, ...} を返す
        auth_result = real_login({
            "username":           username,
            "password":           password,
            "client_cert_fp":     client_fp
        })

        # 認証成功
        return jsonify(auth_result), 200

    except Exception as e:
        # 認証失敗または内部エラー
        logger.warning("Authentication failed: %s", e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 401

app = Flask(__name__)
app.register_blueprint(device_auth_bp)

if __name__ == "__main__":
    # 5050番で起動
    app.run(host="0.0.0.0", port=5050, debug=True)