# sending_dapps/transaction.py
"""
transaction.py

ユーザー入力データから送信トランザクションを整形し、
不変部分のみから固定ハッシュを算出する処理を実装します。
（フロントエンド用のプレビュー機能で使う想定です。）
"""

import uuid
import json
import hashlib
import random
from datetime import datetime, timezone

# フロント／プレビュー用の不変フィールドリスト
IMMUTABLE_FIELDS = [
    "sender", "receiver", "to_wallet", "from_wallet", "amount",
    "transaction_id", "verifiable_credential", "subject", "action_level",
    "dimension", "fluctuation", "organism_name", "sender_municipality",
    "receiver_municipality", "details", "goods_or_money", "location",
    "proof_of_place", "encrypted_message", "pq_public_key", "signature",
    "account_title"
]

def _stub_encrypt(message: str, public_key: str = "") -> str:
    """
    ダミー暗号化: 文字列を逆順に返す
    """
    return message[::-1] if isinstance(message, str) else ""

def prepare_transaction(data: dict) -> dict:
    """
    フロント側で見せる“暫定”トランザクション。
    実際のサーバー側では独自に暗号化・署名を行うため、ここはプレビュー用。
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
    tx = {
        "sender":                data.get("sender", ""),
        "receiver":              data.get("receiver", ""),
        "from_wallet":           data.get("sender_wallet", ""),
        "to_wallet":             data.get("receiver_wallet", ""),
        "amount":                float(data.get("amount", 0)),
        "timestamp":             now,
        "transaction_id":        str(uuid.uuid4()),
        "verifiable_credential": data.get("verifiable_credential", ""),
        "subject":               data.get("subject", ""),
        "action_level":          data.get("action_level", ""),
        "dimension":             data.get("dimension", ""),
        "fluctuation":           data.get("fluctuation", ""),
        "organism_name":         data.get("organism_name", ""),
        "sender_municipality":   data.get("sender_municipality", ""),
        "receiver_municipality": data.get("receiver_municipality", ""),
        "details":               data.get("details", ""),
        "goods_or_money":        data.get("goods_or_money", ""),
        "location":              data.get("location", ""),
        "proof_of_place":        data.get("proof_of_place", ""),
        "account_title":         data.get("account_title", ""),
        "status":                "send_pending",
        "created_at":            now,
        "attributes":            data.get("attributes", {})
    }

    # メッセージ暗号化 (stub)
    message = data.get("details", "")
    tx["encrypted_message"] = _stub_encrypt(message, public_key="stub")

    # 鍵生成と署名 (ダミー)
    pq_pub = uuid.uuid4().hex
    pq_priv = uuid.uuid4().hex
    tx["pq_public_key"] = pq_pub

    # 署名生成 (stub: トランザクションデータ + ダミー秘密鍵 を SHA-256)
    data_str = json.dumps({k: tx[k] for k in IMMUTABLE_FIELDS if k in tx}, sort_keys=True)
    signature_hex = hashlib.sha256((data_str + pq_priv).encode()).hexdigest()
    tx["signature"] = signature_hex

    # 固定ハッシュ計算
    immutable_data = {k: tx[k] for k in IMMUTABLE_FIELDS if k in tx}
    fixed_hash = hashlib.sha256(json.dumps(immutable_data, sort_keys=True).encode()).hexdigest()
    tx["transaction_hash"] = fixed_hash

    # 仕訳・評価・DPoS・Wallet などの処理 (ダミー実装)
    journal_entry = {
        "journal_id":     uuid.uuid4().hex,
        "transaction_id": tx["transaction_id"],
        "amount":         tx["amount"],
        "timestamp":      tx["timestamp"],
        "status":         tx["status"]
    }
    filename = f"journal_{journal_entry['journal_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(journal_entry, f, indent=2, ensure_ascii=False)
    print(f"[Journal] 仕訳保存完了: {filename}")

    metrics = {"evaluation_score": random.uniform(0.5, 1.0)}
    print(f"[Metrics] 評価指標記録: {json.dumps(metrics, ensure_ascii=False)}")

    def elect(role, municipalities):
        return municipalities[0] if municipalities else "default_rep"
    tx["sender_representative"] = elect("sender", [data.get("sender_municipality", "")])
    tx["receiver_representative"] = elect("receiver", [data.get("receiver_municipality", "")])

    print(f"[Wallet] {tx['sender']}→{tx['receiver']} {tx['amount']} の送金処理を実施。")
    tx["status"] = "send_complete"

    return tx
