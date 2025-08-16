# user_manager/user_db.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
import json
import boto3
from user_manager.config import DYNAMODB_TABLE, S3_BUCKET
from user_manager.user_model import User

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
table = dynamodb.Table(DYNAMODB_TABLE)
s3 = boto3.client('s3', region_name="us-east-1")

def save_user(user: User) -> str:
    user_item = user.to_dict()
    try:
        table.put_item(Item=user_item)
        logger.info("DynamoDB 保存成功: %s", user.uuid)
    except Exception as e:
        logger.error("DynamoDB 保存エラー: %s", e)
        raise
    try:
        s3.put_object(Bucket=S3_BUCKET, Key=f"users/{user.uuid}.json", Body=json.dumps(user_item))
        logger.info("S3 保存成功: %s", user.uuid)
    except Exception as e:
        logger.error("S3 保存エラー: %s", e)
        raise
    return user.uuid

def get_user(user_uuid: str) -> User:
    try:
        response = table.get_item(Key={"uuid": user_uuid, "session_id": "REGISTRATION"})
        if "Item" in response:
            logger.info("ユーザー取得成功: %s", user_uuid)
            return User.from_dict(response["Item"])
        else:
            logger.warning("ユーザーが見つかりません: %s", user_uuid)
            return None
    except Exception as e:
        logger.error("ユーザー取得エラー: %s", e)
        raise

def update_user(user_uuid: str, update_data: dict) -> User:
    update_expr = "SET " + ", ".join([f"{k}=:{k}" for k in update_data.keys()])
    expr_values = {f":{k}": v for k, v in update_data.items()}
    try:
        response = table.update_item(
            Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW"
        )
        updated_item = response.get("Attributes")
        logger.info("ユーザー更新成功: %s", user_uuid)
        s3.put_object(Bucket=S3_BUCKET, Key=f"users/{user_uuid}.json", Body=json.dumps(updated_item))
        return User.from_dict(updated_item)
    except Exception as e:
        logger.error("ユーザー更新エラー: %s", e)
        raise
