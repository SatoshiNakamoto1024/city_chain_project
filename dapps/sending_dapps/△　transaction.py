# dapps\sending_dapps\transaction.py
"""
transaction.py

ユーザー入力データから送信トランザクションを整形し、
不変部分のみから固定ハッシュを算出する処理を実装します。
"""

import uuid
import json
import hashlib
import random
from datetime import datetime, timezone

# 各種スタブ実装
def ntru_encrypt(message, public_key):
    return message[::-1]

def generate_dilithium_keys():
    return uuid.uuid4().hex, uuid.uuid4().hex

def sign_transaction(transaction_data, private_key):
    data_str = json.dumps(transaction_data, sort_keys=True)
    return hashlib.sha256((data_str + private_key).encode()).hexdigest()

def generate_journal_entry(transaction):
    return {
        "journal_id":     uuid.uuid4().hex,
        "transaction_id": transaction["transaction_id"],
        "amount":         transaction["amount"],
        "timestamp":      transaction["timestamp"],
        "status":         transaction["status"]
    }

def save_journal_entry(journal_entry):
    filename = f"journal_{journal_entry['journal_id']}.json"
    with open(filename, "w") as f:
        json.dump(journal_entry, f, indent=2)
    print(f"[Journal] 仕訳保存完了: {filename}")

def record_evaluation_metrics(transaction):
    metrics = {"evaluation_score": random.uniform(0.5, 1.0)}
    print(f"[Metrics] 評価指標記録: {json.dumps(metrics)}")
    return metrics

def elect_representative(role, municipalities):
    return random.choice(municipalities) if municipalities else "default_rep"

def process_wallet(transaction):
    print(f"[Wallet] {transaction['sender']}→{transaction['receiver']} {transaction['amount']} の送金処理を実施。")
    return True

IMMUTABLE_FIELDS = [
    "sender", "receiver", "to_wallet", "from_wallet", "amount",
    "transaction_id", "verifiable_credential", "subject", "action_level",
    "dimension", "fluctuation", "organism_name", "sender_municipality",
    "receiver_municipality", "sender_municipal_id", "receiver_municipal_id",
    "details", "goods_or_money", "location", "proof_of_place",
    "encrypted_message", "pq_public_key", "signature"
]

def prepare_transaction(data):
    transaction = {
        "sender":                data.get('sender', ''),
        "receiver":              data.get('receiver', ''),
        "to_wallet":             data.get('receiver_wallet', ''),
        "from_wallet":           data.get('sender_wallet', ''),
        "amount":                float(data.get('amount', 0)),
        "timestamp":             datetime.now(timezone.utc).isoformat() + "Z",
        "transaction_id":        str(uuid.uuid4()),
        "verifiable_credential": data.get('verifiable_credential', ''),
        "subject":               data.get('subject', ''),
        "action_level":          data.get('action_level', ''),
        "dimension":             data.get('dimension', ''),
        "fluctuation":           data.get('fluctuation', ''),
        "organism_name":         data.get('organism_name', ''),
        "sender_municipality":   data.get('sender_municipality', ''),
        "receiver_municipality": data.get('receiver_municipality', ''),
        "sender_municipal_id":   data.get('sender_municipality', ''),
        "receiver_municipal_id": data.get('receiver_municipality', ''),
        "details":               data.get('details', ''),
        "goods_or_money":        data.get('goods_or_money', ''),
        "location":              data.get('location', ''),
        "proof_of_place":        data.get('proof_of_place', ''),
        "status":                "send_pending",
        "created_at":            datetime.now(timezone.utc).isoformat() + "Z",
        "attributes":            data.get("attributes", {})
    }

    # メッセージ暗号化 (stub)
    message = data.get('message', '')
    transaction["encrypted_message"] = (
        ntru_encrypt(message, public_key="stub") if message else ""
    )

    # 鍵生成と署名
    pq_pub, pq_priv = generate_dilithium_keys()
    transaction["pq_public_key"] = pq_pub
    signature_hex = sign_transaction(transaction, pq_priv)
    transaction["signature"] = signature_hex

    # 固定ハッシュ計算
    immutable_data = {k: transaction[k] for k in IMMUTABLE_FIELDS if k in transaction}
    fixed_hash = hashlib.sha256(
        json.dumps(immutable_data, sort_keys=True).encode()
    ).hexdigest()
    transaction["transaction_hash"] = fixed_hash

    # 仕訳・評価・DPoS・Wallet など
    journal_entry = generate_journal_entry(transaction)
    save_journal_entry(journal_entry)
    record_evaluation_metrics(transaction)
    transaction["sender_representative"]   = elect_representative('sender', [data.get('sender_municipality', '')])
    transaction["receiver_representative"] = elect_representative('receiver', [data.get('receiver_municipality', '')])
    process_wallet(transaction)
    transaction["status"] = "send_complete"

    return transaction


if __name__ == "__main__":
    # 動作確認用スタンドアロン
    dummy = {
        "sender": "Alice", "receiver": "Bob",
        "sender_wallet": "alice_wallet", "receiver_wallet": "bob_wallet",
        "amount": "123.45", "message": "Hello, Bob!",
        "verifiable_credential": "cred", "subject": "Payment",
        "action_level": "high", "dimension": "global", "fluctuation": "none",
        "organism_name": "Org", "sender_municipality": "CityA",
        "receiver_municipality": "CityB", "details": "Service",
        "goods_or_money": "money", "location": "Tokyo",
        "proof_of_place": "GPS", "attributes": {"priority": "urgent"}
    }
    tx = prepare_transaction(dummy)
    print(json.dumps(tx, indent=2, ensure_ascii=False))
