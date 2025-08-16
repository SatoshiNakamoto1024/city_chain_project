# login/wallet/wallet_db.py
from decimal import Decimal
from boto3.dynamodb.conditions import Key
import boto3, logging
from .wallet_model import Wallet
from .config import AWS_REGION, WALLET_TABLE

logger = logging.getLogger(__name__)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table    = dynamodb.Table(WALLET_TABLE)

# ---------- 共通ヘルパ ----------
def _to_ddb(item: Wallet) -> dict:
    return {
        "wallet_address": item.wallet_address,
        "user_uuid":      item.user_uuid,
        "balance":        Decimal(str(item.balance))
    }

def _from_ddb(d: dict) -> Wallet:
    return Wallet(
        wallet_address=d["wallet_address"],
        user_uuid=d["user_uuid"],
        balance=Decimal(str(d.get("balance", "0")))
    )

# ---------- Public API ----------
def save_wallet(item: Wallet) -> None:
    table.put_item(Item=_to_ddb(item))

def get_wallet_by_address(addr: str) -> Wallet | None:
    resp = table.get_item(Key={"wallet_address": addr})
    if "Item" in resp:
        return _from_ddb(resp["Item"])
    return None

def update_balance(wallet_address: str, delta: float) -> float:
    """atomic に残高を加算して新残高を float で返す"""
    response = table.update_item(
        Key={"wallet_address": wallet_address},
        UpdateExpression="SET balance = if_not_exists(balance, :zero) + :delta",
        ExpressionAttributeValues={
            ":delta": Decimal(str(delta)),
            ":zero":  Decimal("0"),
        },
        ReturnValues="UPDATED_NEW",
    )
    return float(response["Attributes"]["balance"])

def get_wallet_by_user_uuid(user_uuid: str) -> Wallet | None:
    resp = table.query(
        IndexName="user_index",
        KeyConditionExpression=Key("user_uuid").eq(user_uuid),
        Limit=1,
    )
    items = resp.get("Items", [])
    return _from_ddb(items[0]) if items else None
