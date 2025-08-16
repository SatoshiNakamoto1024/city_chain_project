# auth.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import jwt
import logging
import boto3
from flask import request
from auth_py.config import (
    DYNAMODB_TABLE, S3_BUCKET, SNS_TOPIC_ARN, JWT_SECRET,
    PASSWORD_SALT_SIZE, LOGIN_HISTORY
)
from auth_py.crypto import dilithium

# AWSクライアント初期化
dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
table = dynamodb.Table(DYNAMODB_TABLE)
history_table = dynamodb.Table(LOGIN_HISTORY)
s3 = boto3.client('s3', region_name="us-east-1")
sns_client = boto3.client('sns', region_name="us-east-1")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_salt():
    return os.urandom(PASSWORD_SALT_SIZE).hex()

def hash_password(password, salt):
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def generate_jwt(user_uuid):
    payload = {
        "uuid": user_uuid,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded["uuid"]
    except jwt.ExpiredSignatureError:
        logger.warning("JWT期限切れ")
        return None
    except Exception as e:
        logger.error("JWTエラー: %s", e)
        return None

def save_login_history(user_uuid):
    try:
        history_item = {
            "uuid": user_uuid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "unknown")
        }
        history_table.put_item(Item=history_item)
        logger.info("ログイン履歴を保存しました: %s", history_item)
    except Exception as e:
        logger.warning("ログイン履歴の保存に失敗: %s", e)

def register_user(registration_data):
    user_uuid = str(uuid.uuid4())
    salt = generate_salt()
    password_hash = hash_password(registration_data["password"], salt)
    public_key, private_key = dilithium.generate_keypair()

    user_item = {
        "uuid": user_uuid,
        "name": registration_data.get("name", ""),
        "birth_date": registration_data.get("birth_date", ""),
        "address": registration_data.get("address", ""),
        "mynumber": registration_data.get("mynumber", ""),
        "email": registration_data.get("email", ""),
        "phone": registration_data.get("phone", ""),
        "password_hash": password_hash,
        "salt": salt,
        "public_key": public_key,
        "client_cert_fp": registration_data.get("client_cert_fp"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        table.put_item(Item=user_item)
    except Exception as e:
        raise Exception(f"DynamoDB 保存エラー: {e}")

    try:
        s3.put_object(Bucket=S3_BUCKET, Key=f"users/{user_uuid}.json", Body=json.dumps(user_item))
    except Exception as e:
        raise Exception(f"S3 保存エラー: {e}")

    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=f"登録完了: ユーザーID: {user_uuid}",
            Subject="【通知】ユーザー登録完了"
        )
    except Exception as e:
        logger.error("SNS 通知エラー: %s", e)

    jwt_token = generate_jwt(user_uuid)

    return {
        "uuid": user_uuid,
        "jwt_token": jwt_token,
        "public_key": public_key,
        "private_key": private_key
    }

def login_user(login_data):
    username = login_data.get("username")
    password = login_data.get("password")
    input_fp = login_data.get("client_cert_fp")

    if not username or not password or not input_fp:
        raise Exception("username, password, client_cert_fp are required")

    try:
        response = table.scan(
            FilterExpression="username = :uname",
            ExpressionAttributeValues={":uname": username}
        )
        users = response.get("Items", [])
        if not users:
            raise Exception("ユーザーが見つかりません")

        user_item = users[0]
    except Exception as e:
        raise Exception(f"DynamoDB エラー: {e}")

    salt = user_item.get("salt")
    stored_hash = user_item.get("password_hash")
    stored_fp = user_item.get("client_cert_fp")
    input_hash = hash_password(password, salt)

    if not hmac.compare_digest(stored_hash, input_hash):
        raise Exception("Password does not match")
    if stored_fp != input_fp:
        raise Exception("Client certificate fingerprint mismatch")

    jwt_token = generate_jwt(user_item["uuid"])

    # ✅ ログイン履歴を保存
    save_login_history(user_item["uuid"])

    return {
        "jwt_token": jwt_token,
        "uuid": user_item["uuid"],
        "username": user_item["username"],
        "message": "Login successful"
    }
