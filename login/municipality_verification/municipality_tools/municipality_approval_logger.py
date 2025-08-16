# municipality_verification/municipality_tools/municipality_approval_logger.py

import os
import logging
from datetime import datetime
import boto3

# 環境変数からリージョンとテーブル名を取得
AWS_REGION         = os.getenv("AWS_REGION", "us-east-1")
APPROVAL_LOG_TABLE = os.getenv("APPROVAL_LOG_TABLE", "MunicipalApprovalLogTable")

dynamodb            = boto3.resource("dynamodb", region_name=AWS_REGION)
approval_log_table  = dynamodb.Table(APPROVAL_LOG_TABLE)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def log_approval(uuid: str,
                 action: str,
                 approver_id: str,
                 reason: str = None,
                 client_ip: str = None) -> None:
    """
    承認ログを DynamoDB に記録する。
    - uuid: 承認対象ユーザーの UUID
    - action: "approve" または "reject"
    - approver_id: 承認操作を行った職員の staff_id
    - reason: 承認時の理由（任意）
    - client_ip: クライアント IP（任意）
    """
    item = {
        # log_id に一意性を持たせるため、UUID＋現在時刻
        "log_id":      f"{uuid}_{datetime.utcnow().isoformat()}",
        "uuid":        uuid,
        "action":      action,
        "approver_id": approver_id,
        "reason":      reason or "",
        "client_ip":   client_ip or "unknown",
        "timestamp":   datetime.utcnow().isoformat() + "Z"
    }
    try:
        approval_log_table.put_item(Item=item)
        logger.info("承認ログ記録: %s", item["log_id"])
    except Exception as e:
        logger.error("承認ログ記録失敗: %s", e)
