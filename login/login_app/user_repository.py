# login_app/user_repository.py
"""
UsersTable への CRUD ラッパ
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from login_app.config import USERS_TABLE, AWS_REGION
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_tb = dynamodb.Table(USERS_TABLE)

def get_user(uuid_: str) -> dict | None:
    resp = users_tb.get_item(
        Key={"uuid": uuid_, "session_id": "USER_PROFILE"},
        ConsistentRead=True
    )
    return resp.get("Item")
