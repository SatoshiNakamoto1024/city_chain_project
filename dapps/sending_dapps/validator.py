# sending_dapps/validator.py
"""
validator.py

トランザクションの固定ハッシュ整合性を検証します。
"""

import json
import hashlib

# transaction.py と同じ定義
IMMUTABLE_FIELDS = [
    "sender", "receiver", "to_wallet", "from_wallet", "amount",
    "transaction_id", "verifiable_credential", "subject", "action_level",
    "dimension", "fluctuation", "organism_name", "sender_municipality",
    "receiver_municipality", "details", "goods_or_money", "location",
    "proof_of_place", "encrypted_message", "pq_public_key", "signature",
    "account_title"
]

def validate_transaction(transaction: dict) -> bool:
    """
    transaction_hash と、不変フィールドから再計算したハッシュが一致するかチェック。
    """
    immutable = {k: transaction[k] for k in IMMUTABLE_FIELDS if k in transaction}
    h = hashlib.sha256(json.dumps(immutable, sort_keys=True).encode()).hexdigest()
    return h == transaction.get("transaction_hash", "")
