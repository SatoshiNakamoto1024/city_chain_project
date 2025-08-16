# session_manager/session_manager.py

import uuid
import logging
from datetime import datetime
import boto3
from session_manager.config import LOGIN_HISTORY_TABLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
login_table = dynamodb.Table(LOGIN_HISTORY_TABLE)

def record_login(user_uuid: str, ip_address: str = "unknown"):
    """
    ユーザーがログインした際の記録を DynamoDB に保存。
    セッションIDを生成し、login_timeに現在時刻を設定。
    """
    session_data = {
        "uuid": user_uuid,
        "session_id": str(uuid.uuid4()),
        "login_time": datetime.utcnow().isoformat(),
        "ip_address": ip_address,
        "status": "active",
    }
    try:
        login_table.put_item(Item=session_data)
        logger.info("Login record saved: user=%s, session_id=%s", user_uuid, session_data["session_id"])
    except Exception as e:
        logger.error("Login record 保存エラー: %s", e)
        raise
