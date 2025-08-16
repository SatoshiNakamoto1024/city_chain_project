# File: user_manager/user_service.py

import sys
import os
# user_manager の１つ上をパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import logging
import base64
from datetime import datetime

from user_manager.user_model import User
from user_manager.user_db import save_user, get_user, update_user
from user_manager.user_validation import validate_email, validate_mynumber, validate_password
from user_manager.password_manager import hash_password, generate_salt
from cryptography.hazmat.primitives import serialization

try:
    import rsa_encrypt
except Exception as e:
    print("[ERROR] rsa_encrypt のインポートに失敗:", e)
    raise

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def update_user_profile(user_uuid: str, update_data: dict) -> dict:
    if "email" in update_data:
        validate_email(update_data["email"])
    if "mynumber" in update_data:
        validate_mynumber(update_data["mynumber"])
    update_data["updated_at"] = datetime.utcnow().isoformat()
    updated_user = update_user(user_uuid, update_data)
    return updated_user.to_dict()


def change_user_password(user_uuid: str, current_password: str, new_password: str) -> dict:
    user = get_user(user_uuid)
    if not user:
        raise ValueError("ユーザーが見つかりません")

    import binascii
    salt_hex = user.salt
    try:
        salt_bytes = binascii.unhexlify(salt_hex)
    except Exception:
        salt_bytes = salt_hex.encode("utf-8")

    if hash_password(current_password, salt_bytes) != user.password_hash:
        raise ValueError("現在のパスワードが正しくありません")

    validate_password(new_password)
    new_salt = generate_salt()
    new_hash = hash_password(new_password, new_salt)

    update_data = {
        "password_hash": new_hash,
        "salt":           new_salt.hex(),
        "updated_at":     datetime.utcnow().isoformat()
    }
    updated_user = update_user(user_uuid, update_data)
    return updated_user.to_dict()


def update_user_keys(user_uuid: str, rsa_pub_pem: str) -> dict:
    """
    1) Dilithium 鍵ペアを生成
    2) DDB に public key を保存
    3) secret key をクライアントから渡された RSA 公開鍵で暗号化して返却
    """
    user = get_user(user_uuid)
    if not user:
        raise ValueError("ユーザーが見つかりません")

    # 1) Dilithium 鍵ペア生成（Rust/PyO3 バインディング）
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ntru", "dilithium-py")))
    from app_dilithium import create_keypair
    new_pub, new_sec = create_keypair()

    # 2) DynamoDB に保存
    update_data = {
        "dilithium_public_key": new_pub.hex(),
        "updated_at":           datetime.utcnow().isoformat()
    }
    updated = update_user(user_uuid, update_data)

    # 3) RSA 公開鍵で secret を暗号化
    rsa_pub = serialization.load_pem_public_key(rsa_pub_pem.encode("utf-8"))
    ciphertext = rsa_encrypt.encrypt_message(rsa_pub, new_sec.hex())
    encrypted_secret = base64.b64encode(ciphertext).decode("utf-8")

    return {
        "success": True,
        "uuid": updated.uuid,
        "dilithium_public_key": updated.dilithium_public_key,
        "encrypted_secret_key_b64": encrypted_secret,  # RSA暗号化済み
        "dilithium_secret_key_b64": base64.b64encode(new_sec).decode("utf-8")  # Kotlin JNI で使う raw secret key
    }


def register_lifeform(data: dict) -> dict:
    fixed = {
        "1次元": "個人(ニックネーム)",
        "2次元": data.get("team_name", ""),
        "3次元": data.get("affiliation", ""),
        "4次元": data.get("municipality", ""),
        "5次元": data.get("state", ""),
        "6次元": data.get("country", ""),
        "7次元": "世界経済",
        "8次元": "人類",
        "9次元": "地球",
        "10次元": "太陽系"
    }
    extra = data.get("extra_dimensions", [])
    all_dims = dict(fixed)
    for i, dim in enumerate(extra, start=1):
        if len(all_dims) >= 30:
            break
        all_dims[f"追加次元_{i}"] = dim

    lifeform_id = f"lifeform-{data.get('user_id','dummy')}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    record = {
        "lifeform_id":   lifeform_id,
        "user_id":       data.get("user_id"),
        "dimensions":    all_dims,
        "registered_at": datetime.utcnow().isoformat() + "Z"
    }

    os.makedirs("user_manager/lifeform/lifeform_data", exist_ok=True)
    path = f"user_manager/lifeform/lifeform_data/{lifeform_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record
