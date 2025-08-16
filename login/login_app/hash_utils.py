# login_app/hash_utils.py
"""
パスワードハッシュの共通ユーティリティ
"""
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash
