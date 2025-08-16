# user_manager/user_service.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import logging
from datetime import datetime
from user_manager.user_model import User
from user_manager.user_db import save_user, get_user, update_user
from user_manager.user_validation import validate_required_fields, validate_email, validate_mynumber, validate_password
from user_manager.password_manager import hash_password, generate_salt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def register_new_user(registration_data: dict) -> dict:
    """
    ユーザー登録処理。auth_py.registration の register_user() を呼ぶのではなく、
    user_manager内で完結する場合の例。
    """
    # 入力検証
    validate_required_fields(registration_data)
    validate_email(registration_data["email"])
    validate_mynumber(registration_data["mynumber"])
    validate_password(registration_data["password"])

    # 新規ユーザーの作成 (User Model)
    user_uuid = "user-" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + os.urandom(2).hex()
    salt = generate_salt()
    pw_hash = hash_password(registration_data["password"], salt)

    user = User(
        uuid=user_uuid,
        name=registration_data["name"],
        birth_date=registration_data["birth_date"],
        address=registration_data["address"],
        mynumber=registration_data["mynumber"],
        email=registration_data["email"],
        phone=registration_data["phone"],
        password_hash=pw_hash,
        salt=salt.hex(),
        public_key="",
        created_at=datetime.utcnow().isoformat()
    )

    # DynamoDB & S3へ保存
    user_id = save_user(user)
    return {
        "success": True,
        "uuid": user_id,
        "message": "User registered successfully."
    }

def update_user_profile(user_uuid: str, update_data: dict) -> dict:
    """
    プロフィールを更新。
    email/mynumberが含まれる場合はvalidate。
    """
    if "email" in update_data:
        validate_email(update_data["email"])
    if "mynumber" in update_data:
        validate_mynumber(update_data["mynumber"])
    update_data["updated_at"] = datetime.utcnow().isoformat()
    updated_user = update_user(user_uuid, update_data)  # user_db.update_user
    return updated_user.to_dict()

def change_user_password(user_uuid: str, current_password: str, new_password: str) -> dict:
    """
    パスワード変更処理。
    current_password が正しいか検証し、新しいパスワードをハッシュ化して保存。
    """
    user = get_user(user_uuid)
    if not user:
        raise ValueError("ユーザーが見つかりません")

    # user.salt は hex文字列で保存している
    user_salt = bytes.fromhex(user.salt)
    current_hash = hash_password(current_password, user_salt)
    if current_hash != user.password_hash:
        raise ValueError("現在のパスワードが正しくありません")

    validate_password(new_password)
    new_salt = generate_salt()
    new_hash = hash_password(new_password, new_salt)

    update_data = {
        "password_hash": new_hash,
        "salt": new_salt.hex()
    }
    updated_user = update_user(user_uuid, update_data)
    return updated_user.to_dict()

def update_user_keys(user_uuid: str) -> dict:
    """
    鍵更新処理例: 新しい公開鍵/秘密鍵を生成して、DynamoDB上のpublic_keyを更新。
    """
    # 例として auth_py/crypto/dilithium などを呼ぶ
    from auth_py.crypto import dilithium
    new_public_key, new_private_key = dilithium.generate_keypair()

    updated_item = update_user(user_uuid, {"public_key": new_public_key})
    result = updated_item.to_dict()
    result["new_private_key"] = new_private_key
    return result

def register_lifeform(data: dict) -> dict:
    """
    生命体情報の登録処理例。
    """
    fixed_dimensions = {
        "1次元": "個人(ニックネーム)",
        "2次元": data.get("team_name", "未設定"),
        "3次元": data.get("affiliation", "未設定"),
        "4次元": data.get("municipality", "未設定"),
        "5次元": data.get("state", "未設定"),
        "6次元": data.get("country", "未設定"),
        "7次元": "世界経済",
        "8次元": "人類",
        "9次元": "地球",
        "10次元": "太陽系"
    }
    extra = data.get("extra_dimensions", [])
    all_dimensions = dict(fixed_dimensions)
    for i, dim in enumerate(extra, start=1):
        if len(all_dimensions) >= 30:
            break
        all_dimensions[f"追加次元_{i}"] = dim

    lifeform_id = "lifeform-" + data.get("user_id", "dummy") + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    record = {
        "lifeform_id": lifeform_id,
        "user_id": data.get("user_id"),
        "dimensions": all_dimensions,
        "registered_at": datetime.utcnow().isoformat() + "Z"
    }
    # ローカル保存 (user_manager/lifeform/lifeform_data/)
    os.makedirs("user_manager/lifeform/lifeform_data", exist_ok=True)
    filepath = f"user_manager/lifeform/lifeform_data/{lifeform_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record
