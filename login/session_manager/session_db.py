# session_manager/session_db.py

import logging
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from session_manager.config import LOGIN_HISTORY_TABLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
login_table = dynamodb.Table(LOGIN_HISTORY_TABLE)

def record_session(session_data: dict):
    """
    新規セッションを DynamoDB に保存する。
    session_data例:
      {"uuid": <str>, "session_id": <str>, "login_time": <iso8601>, "ip_address": <str>, "status": "active"}
    """
    try:
        response = login_table.put_item(Item=session_data)
        logger.info("セッション記録保存成功: %s", session_data.get("session_id"))
        return response
    except Exception as e:
        logger.error("セッション記録保存エラー: %s", e)
        raise

def get_sessions(user_uuid: str) -> list:
    """
    ユーザーのセッション履歴を取得（uuidをHASHキーとしてクエリ）。
    """
    try:
        response = login_table.query(
            KeyConditionExpression=Key('uuid').eq(user_uuid)
        )
        items = response.get("Items", [])
        logger.info("セッション履歴取得: user_uuid=%s, count=%d", user_uuid, len(items))
        return items
    except Exception as e:
        logger.error("セッション履歴取得エラー: %s", e)
        raise

def purge_old_sessions(cutoff_date: datetime):
    """
    cutoff_dateより古いセッションを削除する（スキャンして該当を削除）。
    非効率なので本番ではGSI等の利用を検討。
    """
    try:
        response = login_table.scan()
        items = response.get("Items", [])
        deleted = 0
        for it in items:
            session_time = datetime.fromisoformat(it["login_time"])
            if session_time < cutoff_date:
                login_table.delete_item(Key={
                    "uuid": it["uuid"],
                    "session_id": it["session_id"]
                })
                deleted += 1
        logger.info("古いセッション削除完了: %d件削除", deleted)
    except Exception as e:
        logger.error("古いセッション削除エラー: %s", e)
        raise

def update_session_time(user_uuid: str, session_id: str, new_time: str):
    """
    セッションの login_time を更新する（延長用途など）。
    """
    try:
        response = login_table.update_item(
            Key={"uuid": user_uuid, "session_id": session_id},
            UpdateExpression="SET login_time = :new_time",
            ExpressionAttributeValues={":new_time": new_time},
            ReturnValues="UPDATED_NEW"
        )
        logger.info("セッション更新成功: user_uuid=%s, session_id=%s", user_uuid, session_id)
        return response.get("Attributes")
    except Exception as e:
        logger.error("セッション更新エラー: %s", e)
        raise
