# auth_py/logging/cloud_logger.py
import boto3
from datetime import datetime, timezone
import json
import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOG_GROUP_NAME = os.getenv("CW_LOG_GROUP", "ClientCertLogs")
LOG_STREAM_NAME = os.getenv("CW_LOG_STREAM", f"client_cert_stream_{datetime.utcnow().strftime('%Y%m%d')}")

logs_client = boto3.client("logs", region_name=AWS_REGION)

def init_log_stream():
    # グループ作成（存在しなければ）
    try:
        logs_client.create_log_group(logGroupName=LOG_GROUP_NAME)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass

    # ストリーム作成（存在しなければ）
    try:
        logs_client.create_log_stream(logGroupName=LOG_GROUP_NAME, logStreamName=LOG_STREAM_NAME)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass

sequence_token = None  # 初期化


def log_to_cloudwatch(message: dict):
    global sequence_token
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    log_event = {
        "logGroupName": LOG_GROUP_NAME,
        "logStreamName": LOG_STREAM_NAME,
        "logEvents": [
            {
                "timestamp": timestamp,
                "message": json.dumps(message, ensure_ascii=False)
            }
        ]
    }

    # 🔽 初回 token を取得
    if sequence_token is None:
        try:
            response = logs_client.describe_log_streams(
                logGroupName=LOG_GROUP_NAME,
                logStreamNamePrefix=LOG_STREAM_NAME
            )
            streams = response.get("logStreams", [])
            if streams and "uploadSequenceToken" in streams[0]:
                sequence_token = streams[0]["uploadSequenceToken"]
        except Exception as e:
            logger.error(f"[CloudWatch ERROR] describe_log_streams failed: {e}")

    if sequence_token:
        log_event["sequenceToken"] = sequence_token

    try:
        response = logs_client.put_log_events(**log_event)
        sequence_token = response.get("nextSequenceToken")
    except Exception as e:
        logger.error(f"[CloudWatch ERROR] put_log_events failed: {e}")