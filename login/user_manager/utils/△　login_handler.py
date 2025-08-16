# File: login/user_manager/utils/login_handler.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
from flask import Flask, request, jsonify

from utils.platform_utils import detect_platform_from_headers
from utils.storage_checker import check_server_disk_usage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)

def dummy_auth(username: str, password: str) -> bool:
    """
    簡易的なダミー認証。
    テスト目的なので "admin"/"password" が通ればOKとする。
    """
    return (username == "admin" and password == "password")

@app.route("/login", methods=["POST"])
def login_route():
    """
    テスト用: 100MB以上あればOK、なければダメ、というシンプルなハンドラー。

    フロー（PC or IoTの場合）:
      1) User-Agent や X-Device-Type から "pc" or "iot" と判定
      2) サーバー上のディスク使用量 ("/") を check_server_disk_usage でチェック
      3) 100MB未満なら 403
    
    フロー（Android/iOS/その他の場合）:
      1) クライアントが "client_free_space" (バイト数) を POST したと仮定
      2) それが 100MB以上ならOK、なければ403
    
    最後にダミー認証:
      - username = "admin", password = "password" なら 200
      - それ以外なら 401
    """

    # 1. 端末判定
    platform_type = detect_platform_from_headers(request.headers)
    
    # 2. username/password を JSON or form から取得
    username = request.form.get("username") or request.json.get("username", "")
    password = request.form.get("password") or request.json.get("password", "")

    # 3. クライアント送信の空き容量(バイト)を取得（Android等想定）
    client_free_space = 0
    if request.form.get("client_free_space"):
        client_free_space = int(request.form["client_free_space"])
    elif request.json and request.json.get("client_free_space"):
        client_free_space = int(request.json["client_free_space"])

    logger.info(f"Login request from {platform_type} / client_free_space={client_free_space}")

    # 4. プラットフォームごとに 100MB以上あるか判定
    if platform_type in ["pc", "iot"]:
        # サーバー自身のディスク使用量をチェック
        has_enough = check_server_disk_usage("/")
        if not has_enough:
            return jsonify({"success": False, "message": "Not enough server space"}), 403
    else:
        # Android / iOS / game / car / tv etc.
        # → client_free_space が 100MBあるかどうか
        if client_free_space < 100 * 1024 * 1024:
            return jsonify({"success": False, "message": "Insufficient client storage"}), 403

    # 5. ダミー認証
    if dummy_auth(username, password):
        return jsonify({"success": True, "message": f"Login OK for {platform_type}"}), 200
    else:
        return jsonify({"success": False, "message": "Authentication failed"}), 401


if __name__ == "__main__":
    """
    テスト時:
      1. このファイルを `python login_handler.py` で起動
      2. 別ターミナルから `pytest test_utils.py` などを実行
         (test_utils.py 内部で同じlogin_handler.pyをサブプロセス起動するケースがあればそちらでも可)
    
    本番で使う場合は、app_utils.py を別途本物にする想定。
    """
    app.run(host="0.0.0.0", port=5050, debug=True)
