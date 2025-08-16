# session_manager/session_manager.py

import uuid
import logging
from datetime import datetime
import boto3
from session_manager.config import LOGIN_HISTORY_TABLE

# Dillithium 署名関連
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ntru/dilithium-py")))
from app_dilithium import sign_message  # Rust→PyO3バインディング経由で呼び出し

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
login_table = dynamodb.Table(LOGIN_HISTORY_TABLE)

def record_login(user_uuid: str, ip_address: str = "unknown", secret_key: bytes = None):
    """
    ログイン記録をDynamoDBに保存。オプションでDillithium署名トークンも含める。
    """
    session_id = str(uuid.uuid4())
    login_time = datetime.utcnow().isoformat()

    session_data = {
        "uuid": user_uuid,
        "session_id": session_id,
        "login_time": login_time,
        "ip_address": ip_address,
        "status": "active",
    }

    if secret_key:
        try:
            message = f"{user_uuid}:{session_id}:{login_time}".encode()
            signed_token = sign_message(message, secret_key)
            session_data["dilithium_signed_token"] = signed_token.hex()
        except Exception as e:
            logger.warning("Dillithium署名生成に失敗: %s", e)

    try:
        login_table.put_item(Item=session_data)
        logger.info("Login record saved: user=%s, session_id=%s", user_uuid, session_id)
    except Exception as e:
        logger.error("Login record 保存エラー: %s", e)
        raise


def create_session(user_uuid: str, ip_address: str, secret_key: bytes = None) -> dict:
    """
    セッション作成。必要に応じてDillithium署名付きトークンも返す。
    """
    session_id = str(uuid.uuid4())
    login_time = datetime.utcnow().isoformat()

    session_data = {
        "uuid": user_uuid,
        "session_id": session_id,
        "login_time": login_time,
        "ip_address": ip_address,
        "status": "active",
    }

    if secret_key:
        try:
            message = f"{user_uuid}:{session_id}:{login_time}".encode()
            signed_token = sign_message(message, secret_key)
            session_data["dilithium_signed_token"] = signed_token.hex()
        except Exception as e:
            logger.warning("Dillithium署名生成に失敗: %s", e)

    try:
        login_table.put_item(Item=session_data)
        logger.info("セッション作成: user_uuid=%s, session_id=%s", user_uuid, session_id)
    except Exception as e:
        logger.error("セッション作成エラー: %s", e)
        raise

    return session_data
