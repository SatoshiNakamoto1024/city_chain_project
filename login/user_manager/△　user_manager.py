# user_manager/user_manager.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
import json
import logging
from user_manager.config import DYNAMODB_TABLE, S3_BUCKET

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
table = dynamodb.Table(DYNAMODB_TABLE)
s3 = boto3.client('s3', region_name="us-east-1")

def get_user(user_uuid):
    try:
        response = table.get_item(Key={"uuid": user_uuid})
        if "Item" in response:
            return response["Item"]
        else:
            return None
    except Exception as e:
        logger.error("ユーザー取得エラー: %s", e)
        raise

def update_user(user_uuid, update_data):
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
        return updated_item
    except Exception as e:
        logger.error("ユーザー更新エラー: %s", e)
        raise

def register_user_wrapper(registration_data):
    from auth_py.registration import register_user
    return register_user(registration_data)
