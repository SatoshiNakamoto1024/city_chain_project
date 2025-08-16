# auth_py/login.py
import logging
import hmac
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.db_integration import get_user_from_dynamodb_by_username
from auth_py.password_manager import hash_password
from auth_py.jwt_manager import generate_jwt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def initiate_login(login_data: dict) -> dict:
    """
    ログイン処理  
      - 入力データ："username", "password", "client_cert_fp"（クライアント証明書フィンガープリント）が必要  
      - パスワード検証および、登録済みの証明書フィンガープリントと照合  
      - 両者が一致すれば JWT を発行
    """
    username = login_data.get("username")
    password = login_data.get("password")
    client_cert_fp = login_data.get("client_cert_fp")
    if not username or not password or not client_cert_fp:
        raise Exception("username, password, and client certificate fingerprint are required")
    
    user = get_user_from_dynamodb_by_username(username)
    if not user:
        raise Exception("User not found")
    
    # ── パスワード検証 ───────────────────────────
    stored_hash = user.get("password_hash")
    salt_hex = user.get("salt")
    try:
        salt_bytes = bytes.fromhex(salt_hex)
    except ValueError:
        raise Exception("Invalid salt format in database")

    if not hmac.compare_digest(stored_hash, hash_password(password, salt_bytes)):
        raise Exception("Password does not match")
    
    # ── 証明書 fingerprint 検証 ───────────────────
    stored_cert_fp = user.get("client_cert_fingerprint")
    if stored_cert_fp != client_cert_fp:
        raise Exception("Client certificate fingerprint mismatch")
    
    # ── JWT 発行 ──────────────────────────────────
    token = generate_jwt(user["uuid"])
    logger.info("Login successful: %s", user.get("username"))
    return {"success": True, "jwt_token": token}

# エイリアスとして login_user を追加
def login_user(login_data: dict) -> dict:
    return initiate_login(login_data)

if __name__ == '__main__':
    # テスト用：サンプルデータでログイン処理を実行
    import json
    sample_data = {
        "username": "testuser",
        "password": "testpassword",
        "client_cert_fp": "dummyfingerprint"
    }
    result = login_user(sample_data)
    print("Login result:")
    print(json.dumps(result, ensure_ascii=False, indent=4))
