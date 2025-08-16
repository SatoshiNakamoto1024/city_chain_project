# login/auth_py/db_integration.py
import logging
import json
import boto3
import sys
import os
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from auth_py.config import DYNAMODB_TABLE, S3_BUCKET, SNS_TOPIC_ARN
from auth_py.config import LOGIN_HISTORY
from datetime import datetime, timezone
# ログイン履歴用テーブル
history_table = DYNAMODB_TABLE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# DynamoDB クライアント（AWS）
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION", "us-east-1")
)
users_table = dynamodb.Table(DYNAMODB_TABLE)

# S3 クライアント
s3_client = boto3.client(
    's3',
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

# SNS クライアント
sns_client = boto3.client(
    'sns',
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

def save_user_to_dynamodb(user_item):
    try:
        result = users_table.put_item(Item=user_item)
        logger.info("User saved: %s", user_item.get("uuid"))
        return result
    except Exception as e:
        logger.error("Error saving user: %s", e)
        raise

def get_user_from_dynamodb_by_uuid(user_uuid):
    try:
        response = users_table.get_item(Key={"uuid": user_uuid})
        return response.get("Item")
    except Exception as e:
        logger.error("Error retrieving user: %s", e)
        raise

def get_user_from_dynamodb_by_username(username):
    """
    DynamoDB の GSI 'UsernameIndex' を利用してユーザーを検索する
    ※事前にテーブルに GSI を設定しておく必要があります。
    """
    from boto3.dynamodb.conditions import Key, Attr

    try:
        # まず GSI で高速に query
        resp = users_table.query(
            IndexName="UsernameIndex",
            KeyConditionExpression=Key("username").eq(username),
        )
        items = resp.get("Items", [])
    except ClientError as e:
        # GSI がないなどで ValidationException 相当が上がった場合は scan でフォールバック
        logger.warning("UsernameIndex query failed (%s); falling back to scan", e)
        resp = users_table.scan(
            FilterExpression=Attr("username").eq(username)
        )
        items = resp.get("Items", [])

    return items[0] if items else None

def save_login_history(user_uuid: str, ip: str, user_agent: str):
    """
    ログイン履歴を LOGIN_HISTORY テーブルに保存します。
    """
    item = {
        "uuid":       user_uuid,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "ip":         ip,
        "user_agent": user_agent,
    }
    try:
        history_table.put_item(Item=item)
        logger.info("Login history saved: %s", item)
    except Exception as e:
        logger.warning("Failed to save login history: %s", e)

def update_user_in_dynamodb(user_uuid, update_data):
    update_expr = "SET " + ", ".join([f"{k}=:{k}" for k in update_data.keys()])
    expr_values = {f":{k}": v for k, v in update_data.items()}
    try:
        response = users_table.update_item(
            Key={"uuid": user_uuid},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW"
        )
        updated_item = response.get("Attributes")
        logger.info("DynamoDB updated successfully: %s", user_uuid)
        return updated_item
    except Exception as e:
        logger.error("DynamoDB update error: %s", e)
        raise

def save_user_to_s3(user_item):
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f"users/{user_item.get('uuid')}.json",
            Body=json.dumps(user_item, ensure_ascii=False, indent=4),
            ContentType="application/json"
        )
        logger.info("S3 saved successfully: %s", user_item.get("uuid"))
    except Exception as e:
        logger.error("S3 saving error: %s", e)
        raise

def notify_user_via_sns(message):
    # テスト環境などで SNS を利用しない場合は SNS_TOPIC_ARN に "dummy" を設定しておく
    if SNS_TOPIC_ARN.strip().lower() == "dummy":
        logger.info("SNS_TOPIC_ARN is set to 'dummy'; skipping SNS notification.")
        return
    try:
        sns_client.publish(TopicArn=SNS_TOPIC_ARN, Message=message)
        logger.info("SNS notification succeeded")
    except Exception as e:
        logger.error("SNS notification error: %s", e)
        # SNS のエラーは通知処理の失敗としてログに出力するだけで、例外は上げない
        return
