# user_manager/user_manager.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
import json
import logging
from user_manager.config import USERS_TABLE, S3_BUCKET
from user_manager.user_model import User

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
table = dynamodb.Table(USERS_TABLE)
s3 = boto3.client('s3', region_name="us-east-1")

def get_user(user_uuid: str) -> User:
    """
    ユーザーをDynamoDBから取得してUserモデルで返す
    """
    try:
        response = table.get_item(Key={"uuid": user_uuid})
        if "Item" in response:
            item = response["Item"]
            return User.from_dict(item)
        else:
            return None
    except Exception as e:
        logger.error("ユーザー取得エラー: %s", e)
        raise

def update_user(user_uuid: str, update_data: dict) -> User:
    """
    ユーザー情報を更新し、更新結果をUserモデルで返す
    """
    update_expr = "SET " + ", ".join([f"{k}=:{k}" for k in update_data.keys()])
    expr_values = {f":{k}": v for k, v in update_data.items()}
    try:
        response = table.update_item(
            Key={"uuid": user_uuid},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW"
        )
        updated_item = response.get("Attributes")
        s3.put_object(Bucket=S3_BUCKET, Key=f"users/{user_uuid}.json", Body=json.dumps(updated_item))
        logger.info("ユーザー %s 更新完了", user_uuid)
        return User.from_dict(updated_item)
    except Exception as e:
        logger.error("ユーザー更新エラー: %s", e)
        raise
