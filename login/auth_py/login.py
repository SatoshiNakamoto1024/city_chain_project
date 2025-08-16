# login/auth_py/login.py
"""
login.py

認証フロー本体。
パスワード／証明書フィンガープリントを検証し、
一致すれば JWT を発行します。
"""

import logging
import hmac
from datetime import datetime, timezone
from flask import request
from auth_py.db_integration import (
    get_user_from_dynamodb_by_username,
    save_login_history
)
from auth_py.password_manager import hash_password
from auth_py.jwt_manager import generate_jwt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def login_user(login_data: dict) -> dict:
    """
    ・username, password, client_cert_fp が必要
    ・パスワード／fingerprint を検証
    ・成功すれば {'success': True, 'jwt_token': ..., 'uuid': ...} を返す
    """
    username       = login_data.get("username")
    password       = login_data.get("password")
    client_cert_fp = login_data.get("client_cert_fp")
    if not all([username, password, client_cert_fp]):
        raise ValueError("username, password, client_cert_fp are required")

    user = get_user_from_dynamodb_by_username(username)
    if not user:
        raise ValueError("User not found")

    # パスワード検証
    stored_hash = user["password_hash"]
    salt_hex    = user["salt"]
    if not hmac.compare_digest(stored_hash, hash_password(password, salt_hex)):
        raise ValueError("Password does not match")

    # 証明書 fingerprint 検証
    if user.get("client_cert_fingerprint") != client_cert_fp:
        raise ValueError("Client certificate fingerprint mismatch")

    # JWT 発行
    token = generate_jwt(user["uuid"])

    # ログイン履歴を保存
    save_login_history(
        user_uuid=user["uuid"],
        ip=request.remote_addr or "unknown",
        user_agent=request.headers.get("User-Agent", "unknown")
    )

    logger.info("Login succeeded: %s", username)
    return {"success": True, "jwt_token": token, "uuid": user["uuid"]}