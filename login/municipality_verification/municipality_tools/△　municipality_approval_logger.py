# municipality_verification/municipality_tools/municipality_approval_logger.py

import os
import logging
from datetime import datetime
import boto3

# テスト時に環境変数から値を読み込めるように os.getenv() を使う
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
APPROVAL_LOG_TABLE = os.getenv("APPROVAL_LOG_TABLE", "MunicipalApprovalLogTable")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
approval_log_table = dynamodb.Table(APPROVAL_LOG_TABLE)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def log_approval(uuid: str,
                 action: str,
                 approver_id: str,
                 reason: str = None,
                 client_ip: str = None) -> None:
    """
    承認ログを DynamoDB に記録する。
    - uuid: 承認対象ユーザーやトランザクションの識別子
    - action: 実行されたアクション（例："approved" など）
    - approver_id: 承認者のID（admin_id など）
    - reason: 承認時のコメントや理由（省略可）
    - client_ip: クライアントの IP アドレス（省略可）
    """
    item = {
        # ログIDの一意性を担保するため、uuid とタイムスタンプを組み合わせる
        "log_id": f"{uuid}_{datetime.utcnow().isoformat()}",
        "uuid": uuid,
        "action": action,
        "approver_id": approver_id,
        "reason": reason or "",
        "client_ip": client_ip or "unknown",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        approval_log_table.put_item(Item=item)
        logger.info("承認ログ記録: %s", item["log_id"])
    except Exception as e:
        logger.error("承認ログ記録失敗: %s", e)
