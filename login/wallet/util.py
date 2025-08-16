# login/wallet/util.py
from typing import Optional
from .wallet_db import get_wallet_by_user_uuid, get_wallet_by_address

def get_wallet_address_by_user(user_uuid: str) -> Optional[str]:
    """
    user_uuid に紐づく wallet_address を取得。
    存在しない場合は None を返す。
    """
    wallet = get_wallet_by_user_uuid(user_uuid)
    return wallet.wallet_address if wallet else None

def get_balance_by_user(user_uuid: str) -> float:
    """
    user_uuid に紐づく残高 balance を取得。
    """
    wallet = get_wallet_by_user_uuid(user_uuid)
    return float(wallet.balance) if wallet else 0.0

def get_balance_by_wallet(wallet_address: str) -> float:
    """
    wallet_address に紐づく残高 balance を取得。
    """
    wallet = get_wallet_by_address(wallet_address)
    return float(wallet.balance) if wallet else 0.0

def is_wallet_valid(wallet_address: str) -> bool:
    """
    wallet_address が WalletsTable に存在するかをチェック。
    """
    wallet = get_wallet_by_address(wallet_address)
    return wallet is not None
