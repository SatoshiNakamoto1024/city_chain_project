# login/wallet/wallet_service.py
import uuid
from datetime import datetime
import logging
from .wallet_model import Wallet
from .wallet_db    import (
    save_wallet,
    get_wallet_by_user_uuid,
    get_wallet_by_address,
    update_balance
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------- Public API ----------

def create_wallet_for_user(user_uuid: str) -> Wallet:
    """
    既に存在すればそれを返す。無ければ新規作成。
    """
    wallet = get_wallet_by_user_uuid(user_uuid)
    if wallet:
        logger.info("Wallet already exists for %s", user_uuid)
        return wallet

    wallet_address = f"wallet-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    wallet = Wallet(
        wallet_address=wallet_address,
        user_uuid=user_uuid,
        balance=0.0,
        created_at=now,
        updated_at=now
    )
    save_wallet(wallet)
    return wallet

def increment_balance(wallet_address: str, amount_delta: float) -> float:
    """
    正数: 入金 / 負数: 出金。戻り値は残高。
    """
    new_balance = update_balance(wallet_address, amount_delta)
    logger.info("Wallet %s balance updated → %.2f", wallet_address, new_balance)  
    return new_balance

# ---------- Convenience ----------
def get_wallet_by_user(user_uuid: str):
    return get_wallet_by_user_uuid(user_uuid)

def get_wallet(addr: str):
    return get_wallet_by_address(addr)
