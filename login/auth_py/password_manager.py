# login/auth_py/password_manager.py
import hashlib
PASSWORD_SALT_SIZE = 16               # 例：16 bytes

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.config import PASSWORD_SALT_SIZE

def generate_salt():
    return os.urandom(PASSWORD_SALT_SIZE)  # bytes のまま返す（←おすすめ）

def hash_password(password: str, salt: str | bytes) -> str:
    """
    salt が str(hex) なら bytes へ戻してから SHA‑256(salt + pw)
    """
    if isinstance(salt, str):
        salt = bytes.fromhex(salt)  # str の場合は bytes に変換
    return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
