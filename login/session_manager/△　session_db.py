# session_manager/session_db.py
import logging
import boto3
import json
from datetime import datetime
from boto3.dynamodb.conditions import Key
from session_manager.config import LOGIN_HISTORY_TABLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# ハンドラー設定（必要に応じて）
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# DynamoDB クライアント初期化（リージョンは適宜設定）
dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
# ここでは実際に作成済みの LoginHistory テーブルを参照する
login_table = dynamodb.Table(LOGIN_HISTORY_TABLE)

def record_session(session_data: dict):
    """
    セッションデータを DynamoDB に保存します。
    session_data は辞書形式で、例：
      {'uuid': ..., 'session_id': ..., 'login_time': ..., 'ip_address': ..., 'status': ...}
    """
    try:
        response = login_table.put_item(Item=session_data)
        logger.info("セッション記録保存成功: session_id=%s", session_data.get("session_id"))
        return response
    except Exception as e:
        logger.error("セッション記録保存エラー: %s", e)
        raise

def get_sessions(user_uuid: str) -> list:
    """
    指定ユーザーのセッション履歴を DynamoDB から取得します。
    'uuid' に基づいてクエリします。
    """
    try:
        response = login_table.query(
            KeyConditionExpression=Key('uuid').eq(user_uuid)
        )
        sessions = response.get("Items", [])
        logger.info("セッション履歴取得成功: ユーザー %s (件数=%d)", user_uuid, len(sessions))
        return sessions
    except Exception as e:
        logger.error("セッション履歴取得エラー: %s", e)
        raise

def purge_old_sessions(cutoff_date: datetime):
    """
    指定日時以前のセッションを削除します。
    ※ 効率的な削除にはインデックス等を利用すべきですが、ここではスキャンして削除する例です。
    """
    try:
        response = login_table.scan()
        items = response.get("Items", [])
        deleted = 0
        for item in items:
            session_time = datetime.fromisoformat(item.get("login_time"))
            if session_time < cutoff_date:
                # 'uuid' と 'session_id' をキーとして想定
                login_table.delete_item(Key={"uuid": item["uuid"], "session_id": item["session_id"]})
                deleted += 1
        logger.info("古いセッション削除完了: %d 件削除", deleted)
    except Exception as e:
        logger.error("古いセッション削除エラー: %s", e)
        raise

# update_session_time の追加（本番用に実際の DynamoDB 更新を行う）
def update_session_time(user_uuid: str, session_id: str, new_time: str):
    try:
        response = login_table.update_item(
            Key={"uuid": user_uuid, "session_id": session_id},
            UpdateExpression="SET login_time = :new_time",
            ExpressionAttributeValues={":new_time": new_time},
            ReturnValues="UPDATED_NEW"
        )
        logger.info("セッション更新成功: %s", session_id)
        return response.get("Attributes")
    except Exception as e:
        logger.error("セッション更新エラー: %s", e)
        raise