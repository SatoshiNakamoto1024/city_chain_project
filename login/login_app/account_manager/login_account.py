# account_manager/login_account.py
"""
共通ログイン：
  role = resident (既定) / staff / admin
"""
from __future__ import annotations
import os, sys, hashlib, hmac, logging, boto3, jwt
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from auth_py.password_manager import hash_password
from login_app.account_manager.config import (
    AWS_REGION, USERS_TABLE, STAFF_TABLE, ADMIN_TABLE,
    JWT_SECRET, JWT_ALGORITHM, JWT_EXP_HOURS
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb   = boto3.resource("dynamodb", region_name=AWS_REGION)
users_tbl  = dynamodb.Table(USERS_TABLE)
staff_tbl  = dynamodb.Table(STAFF_TABLE)
admin_tbl  = dynamodb.Table(ADMIN_TABLE)

def _get_item(role:str, username:str):
    if role == "staff":
        resp = staff_tbl.scan(
            FilterExpression="#s = :u",
            ExpressionAttributeNames={"#s": "staff_id"},
            ExpressionAttributeValues={":u": username},
        )
        return resp.get("Items", [{}])[0]
    if role == "admin":
        # PK+SK の複合なので scan
        resp = admin_tbl.scan(
            FilterExpression="#a = :u",
            ExpressionAttributeNames={"#a": "admin_id"},
            ExpressionAttributeValues={":u": username},
        )
        return resp.get("Items", [{}])[0]
    # resident (UsersTable): username GSI が無い前提で scan
    resp = users_tbl.scan(
        FilterExpression="#u = :u",
        ExpressionAttributeNames={"#u": "username"},
        ExpressionAttributeValues={":u": username},
    )
    return resp.get("Items", [{}])[0]

def _make_jwt(uuid_val:str, role:str)->str:
    return jwt.encode({
        "uuid": uuid_val,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXP_HOURS)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

def login_account(data:dict)->dict:
    role = data.get("role", "resident").lower()
    username = data.get("username")
    password = data.get("password")

    item = _get_item(role, username)
    if not item:
        return {"success": False, "message": "user not found"}

    salt = bytes.fromhex(item["salt"])
    if not hmac.compare_digest(item["password_hash"], hash_password(password, salt)):
        return {"success": False, "message": "invalid credentials"}

    return {
        "success": True,
        "jwt": _make_jwt(item.get("uuid") or item.get("admin_id") or item.get("staff_id"), role),
        "role": role,
    }
