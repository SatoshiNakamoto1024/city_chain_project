# account_manager/app_account_manager.py
"""
app_account_manager.py
----------------------
共通アカウント操作のFacade（住民 / 職員 / 管理者）。

外部コードは次の 3 関数だけ呼び出せばよい:

    create_account(payload: dict) -> dict
    login(payload: dict)          -> dict
    list_staff(municipality_id)   -> list[dict]
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from account_manager.register_account import register_account
from account_manager.login_account    import login_account
from account_manager.config           import (
    AWS_REGION, STAFF_TABLE, ADMIN_TABLE
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb   = boto3.resource("dynamodb", region_name=AWS_REGION)
staff_tbl  = dynamodb.Table(STAFF_TABLE)
admin_tbl  = dynamodb.Table(ADMIN_TABLE)

# ------------------------------------------------------------------ Facade
def create_account(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    role=resident / staff / admin を自動判別して登録。
    * 内部で register_account → registration.register_user が走る
    * 住民は UsersTable、職員は MunicipalStaffs へサマリ複製、
      管理者は AdminsTable へ複製
    """
    logger.info("create_account role=%s user=%s",
                payload.get("role", "resident"), payload.get("username"))
    return register_account(payload)

def login(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    共通ログイン窓口。
    返り値例:
        {"success": True, "jwt": "...", "role": "staff"}
    """
    return login_account(payload)

# ------------------------------------------------------------------ Utilities
def list_staff(municipality_id: str) -> List[Dict[str, Any]]:
    """
    MunicipalStaffs テーブルから該当自治体の職員を一覧取得。
    """
    resp = staff_tbl.query(
        KeyConditionExpression="municipality_id = :m",
        ExpressionAttributeValues={":m": municipality_id},
    )
    return resp.get("Items", [])

def list_admins() -> List[Dict[str, Any]]:
    """
    AdminsTable 全件取得。
    """
    resp = admin_tbl.scan()
    return resp.get("Items", [])
