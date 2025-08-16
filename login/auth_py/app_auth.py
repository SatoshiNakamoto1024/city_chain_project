# login/auth_py/app_auth.py
"""
app_auth.py

フロント API で直接叩くエンドポイント。
PEM ⇄ Finger-Print 変換を自動で行うよう改修済み。
"""

import os, sys, logging, json, base64
from datetime import datetime, timezone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import Flask, request, jsonify
from auth_py.db_integration     import (
    save_user_to_dynamodb as _save_user_,
    notify_user_via_sns,
    save_user_to_s3,
    get_user_from_dynamodb_by_username,
)

# ──────────────────────────────────────────────
# 追加：PEM→FP 変換ユーティリティ
# ──────────────────────────────────────────────
from auth_py.auth_with_cert import cert_pem_to_fingerprint
from auth_py.client_cert_handler import save_cert         # ローカル保存用
from auth_py.fingerprint import normalize_fp
from auth_py.client_cert.dilithium_verify import extract_dilithium_pub_from_spki
# もし NTRU 公開鍵も取り出したい場合は、同じモジュールから下記も import 可能です
from auth_py.client_cert.dilithium_verify import extract_ntru_pub_from_spki

# from infra.logging_setup import configure_logging
# configure_logging()

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] %(asctime)s - %(message)s')
app = Flask(__name__)
app.config['DEBUG'] = True

# ------------------------------------------------------------------------------
# 内部関数・既存 import（循環依存回避のため遅延 import）
# ------------------------------------------------------------------------------
from auth_py.password_manager import generate_salt as _gen_salt_, hash_password as _hash_pw_
from auth_py.client_cert.client_cert import generate_client_certificate as _gen_cert_
from auth_py.cloud_logging.cloud_logger import log_to_cloudwatch as _log_to_cloudwatch


# ──────────────────────────────────────────────
# ラッパー Interface
# ──────────────────────────────────────────────
def log_to_cloudwatch_interface(event: str, payload: dict):
    _log_to_cloudwatch({"event": event, **payload})


def save_user_to_dynamodb_interface(user_data):
    return _save_user_(user_data)


def generate_salt_interface():
    return _gen_salt_()


def hash_password_interface(password, salt):
    return _hash_pw_(password, salt)


def generate_client_certificate_interface(uuid_val, validity_days=365):
    return _gen_cert_(uuid_val, validity_days)


@app.route('/')
def index():
    return "Auth Test App: Use /register (POST) and /login (POST) endpoints."


# ──────────────────────────────────────────────
# 登録エンドポイント
# ──────────────────────────────────────────────
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or request.form.to_dict()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # PEM が来ていれば finger-print を計算
        if pem := data.get("client_cert_pem"):
            fp = cert_pem_to_fingerprint(pem)
            data["client_cert_fp"] = fp
            save_cert(data.get("username", "no_name"), pem)   # ローカル保存
            # 追加: PEMから Dilithium 公開鍵を抽出
            try:
                dilithium_pubkey = extract_dilithium_pub_from_spki(pem.encode())
                data["dilithium_public_key"] = dilithium_pubkey.hex()
            except Exception as e:
                logging.warning("Dilithium 公開鍵の抽出に失敗: %s", e)
        
        from registration.registration import register_user   # 遅延 import
        # registration.registration.register_user は
        # (payload_dict, status_code) を返す仕様なので分岐させる
        result = register_user(data)
 
        if isinstance(result, tuple):
            payload, status = result           # (dict, int)
        else:
            payload, status = result, 200      # 従来通り dict だけ返す実装にも対応

        return jsonify(payload), status

    except Exception as e:
        logging.error("登録エラー: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# ログインエンドポイント
# ──────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or request.form.to_dict()
    username = data.get("username")
    password = data.get("password")
    # ① fingerprint or PEM のどちらかを必須に変更
    pem_or_fp = data.get("client_cert_pem") or data.get("client_cert_fp")
    if not username or not password or not pem_or_fp:
        return jsonify({"success": False,
                        "error": "username, password and client_cert_pem (or fp) are required"}), 400

    # PEM → Finger-Print へ統一
    # PEM か FP かを自動判定して Finger-Print を取得
    def to_fp(pem_or_fp: str) -> str:
        """PEM なら計算、FP ならそのまま正規化"""
        if "BEGIN CERTIFICATE" in pem_or_fp:
            return normalize_fp(cert_pem_to_fingerprint(pem_or_fp))
        else:
            return normalize_fp(pem_or_fp)

    input_fp = to_fp(pem_or_fp)
    data["client_cert_fp"] = input_fp

    # DynamoDB でユーザー取得
    found_item = get_user_from_dynamodb_by_username(username)
    if not found_item:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Finger-Print 照合
    # ❷ 保存済み FP も正規化して照合
    stored_fp = normalize_fp(found_item.get("client_cert_fingerprint", ""))
    if stored_fp != input_fp:
        logging.error("ログインエラー: fingerprint mismatch")
        return jsonify({"success": False, "error": "Client certificate mismatch"}), 401

    try:
        from auth_py.login import login_user   # 遅延 import
        result = login_user(data)
        return jsonify(result), 200

    except Exception as e:
        logging.error("ログインエラー: %s", e)
        return jsonify({"error": str(e)}), 401


# ------------------------------------------------------------------------------
# Blueprint 登録は変更なし
# ------------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from auth_py.revoke_cert_service import client_cert_bp
from user_manager.app_user_manager import user_bp 
from auth_py.client_cert.list_cert_ui import admin_cert_bp
from auth_py.client_cert.certificate_ui import cert_ui_bp

app.register_blueprint(cert_ui_bp)
app.register_blueprint(admin_cert_bp, url_prefix="/client_cert")
app.register_blueprint(client_cert_bp, url_prefix="/client_cert")
app.register_blueprint(user_bp,     url_prefix="/profile")

if __name__ == '__main__':
    app.run(port=5000)
