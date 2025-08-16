# session_manager/session_service.py

import uuid
from datetime import datetime, timedelta
import logging
from session_manager.session_db import record_session, get_sessions, purge_old_sessions, update_session_time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_session(user_uuid: str, ip_address: str) -> dict:
    """
    新しいセッションを生成しDynamoDBに保存。
    """
    session_id = str(uuid.uuid4())
    session_data = {
        "uuid": user_uuid,
        "session_id": session_id,
        "login_time": datetime.utcnow().isoformat(),
        "ip_address": ip_address,
        "status": "active",
    }
    record_session(session_data)
    logger.info("セッション作成: user_uuid=%s, session_id=%s", user_uuid, session_id)
    return session_data

def retrieve_user_sessions(user_uuid: str) -> list:
    """
    ユーザーのセッション履歴を取得。
    """
    sessions = get_sessions(user_uuid)
    # session_id をキーに重複排除
    unique_sessions = {s["session_id"]: s for s in sessions}.values()
    return list(unique_sessions)

def extend_session(user_uuid: str, session_id: str, additional_minutes: int) -> dict:
    """
    セッションの有効期限延長：例として、login_timeを更新する
    """
    new_time = datetime.utcnow().isoformat()
    update_session_time(user_uuid, session_id, new_time)
    return {"session_id": session_id, "new_login_time": new_time}

def purge_sessions(retention_days: int):
    """
    retention_days 日以上前のセッションを削除
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    purge_old_sessions(cutoff_date)
    logger.info("purge_sessions: retention_days=%d で古いセッションを削除しました。", retention_days)
