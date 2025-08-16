# File: android/app_flask.py
"""
最小構成の本番テスト用バックエンド  ― Android Instrumentation Test 用
──────────────────────────────────────────
* Flask 2.x
* cryptography 42.x 以上
* registration.routes.auth_bp を使って
  - /register/                （ユーザー登録）
  - /user/login               （本番ロジックでのログイン）
  - その他 /user/... 系
  をそのままルーティングする
"""

import os, sys, secrets, base64, logging
from datetime import datetime, timezone
from pathlib import Path

# ── パス設定 ──────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]     # <project root>/login まで遡る
sys.path.insert(0, str(ROOT_DIR))                  # login/ を import 可能に
#   login_app, registration, user_manager ... が import 済み前提

# ── Flask ────────────────────────────
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# Blueprint 読み込み（登録／ログイン本番ロジック）
from login_app.register import register_bp
from registration.routes import auth_bp            # ← 追加：/user/login 等
# 既存の user_manager 側 API も使う場合は下記
from user_manager.app_user_manager import user_bp  # optional

app = Flask(__name__)

# Blueprint を **必ず先に** 登録（上から順にマッチ）
app.register_blueprint(register_bp, url_prefix="/register")  # POST /register/
app.register_blueprint(auth_bp)                              # /user/login など
app.register_blueprint(user_bp,  url_prefix="/user")         # /user/keys/update など


logger = logging.getLogger("android.test.api")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# ───────────────────────────────────
# 以降は “テスト専用エンドポイント” のみ残す
#   - /client_cert                （ダミー証明書）
#   - /user/keys/update           （RSA 暗号化 Dilithium SK）
#   - /user/storage_check         （100 MB 予約通知）
# ※ /register/ と /user/login は Blueprint 側に委譲済み
# ───────────────────────────────────

# --------------------------------------------------
# 1) クライアント証明書 “ダミー” 発行
# --------------------------------------------------
@app.route("/client_cert", methods=["POST"])
def client_cert():
    data = request.get_json(force=True)
    uuid   = data.get("uuid")
    logger.info(f"/client_cert  uuid={uuid}")
    dummy_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIBkTCCATegAwIBAgIUY2xpZW50LWR1bW15MBswGjAYBgNVBAMMEWNsaWVudC1k\n"
        "dW1teS1jZXJ0MB4XDTI1MDUxMTAwMDAwMFoXDTM1MDUwODAwMDAwMFowGzEZMBcG\n"
        "A1UEAwwQY2xpZW50LWR1bW15LXV1aWQwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNC\n"
        "AARdummypublickeybytesandmore..................................\n"
        "-----END CERTIFICATE-----\n"
    )
    return jsonify({"pem": dummy_pem}), 200

# --------------------------------------------------
# 2) Dilithium SK を RSA-OAEP で暗号化して返す
# --------------------------------------------------
def _rsa_encrypt(pub_pem: str, plaintext: bytes) -> bytes:
    pub_key = serialization.load_pem_public_key(pub_pem.encode())
    return pub_key.encrypt(
        plaintext,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )

@app.route("/user/keys/update", methods=["POST"])
def user_keys_update():
    j = request.get_json(force=True)
    user_uuid   = j.get("user_uuid")
    rsa_pub_pem = j.get("rsa_pub_pem")
    if not user_uuid or not rsa_pub_pem:
        return jsonify({"success": False, "message": "param missing"}), 400
    logger.info(f"/user/keys/update  uuid={user_uuid[:8]}…")

    secret = secrets.token_bytes(2544)          # ダミー Dilithium SK
    cipher = _rsa_encrypt(rsa_pub_pem, secret)
    return jsonify({
        "encrypted_secret_key_b64": base64.b64encode(cipher).decode()
    }), 200

# --------------------------------------------------
# 3) 100 MB 予約通知をダミー記録
# --------------------------------------------------
@app.route("/user/storage_check", methods=["POST"])
def storage_check():
    j = request.get_json(force=True)
    user_uuid = j.get("userUuid")
    reserved  = j.get("reservedBytes")
    logger.info(f"/user/storage_check uuid={user_uuid[:8]}… reserved={reserved}")
    return jsonify({"success": True}), 200

# ───────────────────────────────────
if __name__ == "__main__":
    # テスト用サーバー起動
    app.run(host="0.0.0.0", port=8888, debug=False)
