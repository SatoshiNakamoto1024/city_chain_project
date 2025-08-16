# login/auth_py/jwt_manager.py

import jwt
from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

def generate_jwt(user_uuid: str) -> str:
    """
    JWT を発行する。
    exp には整数の Unix タイムスタンプを入れる必要がある。
    """
    exp_time = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "uuid": user_uuid,
        "exp": int(exp_time.timestamp())
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt(token: str):
    """
    JWT を検証し、ペイロードを返す。期限切れや破損は例外を投げる。
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as e:
        raise Exception("JWT 期限切れ") from e
    except Exception as e:
        raise Exception(f"JWT検証エラー: {e}") from e
