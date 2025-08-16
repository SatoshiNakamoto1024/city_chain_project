# auth_py/jwt_manager.py
import jwt
from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

def generate_jwt(user_uuid: str) -> str:
    payload = {
        "uuid": user_uuid,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        raise Exception(f"JWT検証エラー: {e}")
