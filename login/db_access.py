# login/db_access.py

"""
DynamoDB / MongoDB へのアクセスをまとめたサンプルモジュール。
実際はモジュールを分ける/ORマッパーを使う/など自由。
"""

import os
import logging
import boto3
from boto3.dynamodb.conditions import Key
import pymongo
from login.config import (
    AWS_REGION, USER_TABLE, S3_BUCKET, SNS_TOPIC_ARN,
    MONGODB_URI, DATABASE_NAME, COLLECTION_NAME
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------- DynamoDB ----------
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USER_TABLE)

# ---------- MongoDB ----------
mongo_client = pymongo.MongoClient(MONGODB_URI)
mongo_db = mongo_client[DATABASE_NAME]
mongo_collection = mongo_db[COLLECTION_NAME]

def get_user_dynamo_by_username_or_email(username: str):
    """
    ユーザー名またはメールアドレスが一致するDynamoDBアイテムを1件返す(Scanベースなので非推奨; PK/GSIが望ましい)
    """
    try:
        resp = users_table.scan()
        items = resp.get("Items", [])
        for it in items:
            if it.get("username") == username or it.get("email") == username:
                return it
        return None
    except Exception as e:
        logger.error("Dynamo get_user scan error: %s", e)
        return None

def put_user_dynamo(user_item: dict):
    """
    DynamoDBへユーザー情報を保存 or 更新
    """
    try:
        users_table.put_item(Item=user_item)
        logger.info("Dynamo put_user success: %s", user_item.get("uuid"))
    except Exception as e:
        logger.error("Dynamo put_user error: %s", e)
        raise

def get_user_mongo(username: str):
    """
    MongoDB上で username が一致するユーザーを1件返す
    """
    try:
        return mongo_collection.find_one({"username": username})
    except Exception as e:
        logger.error("Mongo get_user error: %s", e)
        return None

def insert_user_mongo(user_doc: dict):
    """
    MongoDB にユーザー情報を挿入
    """
    try:
        result = mongo_collection.insert_one(user_doc)
        logger.info("Mongo insert_user success: _id=%s", result.inserted_id)
        return str(result.inserted_id)
    except Exception as e:
        logger.error("Mongo insert_user error: %s", e)
        raise

# 例: S3, SNS もここにまとめてもOK
import boto3
s3 = boto3.client("s3", region_name=AWS_REGION)
sns = boto3.client("sns", region_name=AWS_REGION)

def upload_user_to_s3(user_data: dict):
    """
    S3に user_data (JSON) をアップロード
    """
    import json
    import time
    key = f"users/{user_data['uuid']}_{int(time.time())}.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(user_data, ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        logger.info("S3 upload success: %s", key)
    except Exception as e:
        logger.error("S3 upload error: %s", e)
        raise

def notify_via_sns(message: str):
    """
    SNS通知の例
    """
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="User Notification"
        )
        logger.info("SNS notification success")
    except Exception as e:
        logger.error("SNS publish error: %s", e)
        raise
