# session_manager/session_service.py
import uuid
from datetime import datetime, timedelta
import logging
from session_manager.session_db import record_session, get_sessions, purge_old_sessions

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_session(user_uuid: str, ip_address: str) -> dict:
    """
    新しいセッションを作成し、DynamoDB に記録します。
    セッションIDは UUID を利用。
    """
    session_id = str(uuid.uuid4())
    session_data = {
        "uuid": user_uuid,
        "session_id": session_id,
        "login_time": datetime.utcnow().isoformat(),
        "ip_address": ip_address,
        "status": "active"
    }
    record_session(session_data)
    logger.info("セッション作成完了: %s", session_id)
    return session_data

def retrieve_user_sessions(user_uuid: str) -> list:
    """
    指定されたユーザーのセッション履歴を取得し、重複を排除して返します。
    """
    sessions = get_sessions(user_uuid)
    # セッションIDをキーに重複排除
    unique_sessions = {s["session_id"]: s for s in sessions}.values()
    return list(unique_sessions)

def extend_session(user_uuid: str, session_id: str, additional_minutes: int) -> dict:
    """
    セッションの有効期限を延長する処理（例として、login_time を更新）。
    ※ 本来は有効期限フィールドを設けるべきですが、ここでは単純に login_time を更新する例です。
    """
    # ここでは update_session_time() など、session_db の更新関数を呼ぶことを想定（実装例は以下）
    from session_manager.session_db import update_session_time
    new_time = datetime.utcnow().isoformat()
    update_session_time(user_uuid, session_id, new_time)
    return {"session_id": session_id, "new_login_time": new_time}

def purge_sessions(retention_days: int):
    """
    セッション保持期間に基づき、古いセッションを削除します。
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    purge_old_sessions(cutoff_date)
