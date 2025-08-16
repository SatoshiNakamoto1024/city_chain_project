# session_manager/session_analysis.py

import logging
from datetime import datetime
from boto3.dynamodb.conditions import Key
import boto3
from session_manager.config import LOGIN_HISTORY_TABLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def analyze_sessions(user_uuid: str) -> dict:
    """
    ユーザーのセッション履歴を分析し、平均ログイン間隔・最終ログイン時間・セッション件数を返す。
    """
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    table = dynamodb.Table(LOGIN_HISTORY_TABLE)

    try:
        response = table.query(KeyConditionExpression=Key('uuid').eq(user_uuid))
        sessions = response.get("Items", [])
        if not sessions:
            return {"message": "No sessions found", "average_interval": None, "last_login": None, "session_count": 0}

        # login_time をISO8601とみなし、時系列順に並び替え
        sessions_sorted = sorted(sessions, key=lambda s: s["login_time"])
        intervals = []
        for i in range(1, len(sessions_sorted)):
            t1 = datetime.fromisoformat(sessions_sorted[i-1]["login_time"])
            t2 = datetime.fromisoformat(sessions_sorted[i]["login_time"])
            intervals.append((t2 - t1).total_seconds())

        avg_interval = sum(intervals) / len(intervals) if intervals else None
        last_login = sessions_sorted[-1]["login_time"]
        return {
            "average_interval": avg_interval,
            "last_login": last_login,
            "session_count": len(sessions_sorted)
        }

    except Exception as e:
        logger.error("セッション分析エラー: %s", e)
        raise
