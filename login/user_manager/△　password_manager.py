# user_manager/password_manager.py
import hashlib
import os

def generate_salt(length: int = 16) -> bytes:
    """
    指定された長さのランダムなバイト列（ソルト）を生成する。
    """
    return os.urandom(length)

def hash_password(password: str, salt: bytes) -> str:
    """
    ソルトを加えたパスワードをSHA-256でハッシュ化する。
    """
    return hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
