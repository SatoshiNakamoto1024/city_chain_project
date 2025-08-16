# device_manager/device_db.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
import logging
import os
from device_manager.device_model import Device
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB上に "DevicesTable" などを想定
DEVICES_TABLE = os.getenv("DEVICES_TABLE", "DevicesTable")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
device_table = dynamodb.Table(DEVICES_TABLE)
users_table = dynamodb.Table(USERS_TABLE)

def save_device(device: Device):
    """
    DynamoDBにデバイスを保存
    """
    try:
        device_table.put_item(Item=device.to_dict())
        logger.info("デバイス登録成功: device_id=%s", device.device_id)
    except Exception as e:
        logger.error("デバイス登録失敗: %s", e)
        raise

def get_devices_by_user(user_uuid: str) -> list:
    """
    ユーザーに紐づくデバイス一覧を取得
    ※ 本番ではPK(uuid)でクエリするため、KeySchemaを設定する必要あり
    """
    try:
        resp = device_table.query(
            KeyConditionExpression=Key("uuid").eq(user_uuid)
        )
        items = resp.get("Items", [])
        # from_dict 内で "uuid" を "user_uuid" に変換している
        return [Device.from_dict(i) for i in items]
    except Exception as e:
        logger.error("デバイス一覧取得失敗: %s", e)
        raise

def get_active_devices_count(user_uuid: str) -> int:
    try:
        resp = device_table.query(
            KeyConditionExpression=Key("uuid").eq(user_uuid)
        )
        items = resp.get("Items", [])
        # from_dict 内で "uuid" を "user_uuid" に変換している
        return len([i for i in items if i.get("is_active", True)])
    except Exception as e:
        logger.error("アクティブ端末数取得失敗: %s", e)
        raise

def delete_device(user_uuid: str, device_id: str):
    """
    デバイスを削除 (unbind)
    """
    try:
        device_table.delete_item(
            Key={
                "uuid": user_uuid,
                "device_id": device_id
            }
        )
        logger.info("デバイス削除成功: %s", device_id)
    except Exception as e:
        logger.error("デバイス削除失敗: %s", e)
        raise

def get_primary_session(user_uuid: str):
    try:
        resp = users_table.query(
            KeyConditionExpression=Key("uuid").eq(user_uuid)
        )
        items = resp.get("Items", [])
        return items[0] if items else None
    except Exception as e:
        logger.error("UsersTableのセッション取得失敗: %s", e)
        return None

def delete_primary_session(user_uuid: str, session_id: str):
    try:
        users_table.delete_item(
            Key={"uuid": user_uuid, "session_id": session_id}
        )
        logger.info("UsersTableのセッション削除成功: session_id=%s", session_id)
    except Exception as e:
        logger.error("UsersTableのセッション削除失敗: %s", e)