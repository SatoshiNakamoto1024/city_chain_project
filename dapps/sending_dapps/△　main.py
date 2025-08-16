# main.py
"""
main.py

このモジュールは、送信DApps のエントリーポイントです。
ユーザーからの入力データを受け取り、トランザクションの整形・生成および整合性検証を行い、
生成されたトランザクションデータを出力します。
"""

import json
from transaction import prepare_transaction
from validator import validate_transaction

def main():
    input_data = {
        "sender": "Alice",
        "receiver": "Bob",
        "sender_wallet": "alice_wallet_address",
        "receiver_wallet": "bob_wallet_address",
        "amount": "123.45",
        "message": "Hello, Bob! Here's the payment.",
        "verifiable_credential": "credential_example",
        "subject": "Payment",
        "action_level": "high",
        "dimension": "global",
        "fluctuation": "none",
        "organism_name": "TestOrg",
        "sender_municipality": "CityA",
        "receiver_municipality": "CityB",
        "details": "Payment for services",
        "goods_or_money": "money",
        "location": "Tokyo",
        "proof_of_place": "GPS_data",
        "attributes": {"priority": "urgent"}
    }
    transaction = prepare_transaction(input_data)
    print("整形されたトランザクション:")
    print(json.dumps(transaction, indent=2))
    if validate_transaction(transaction):
        print("[Validator] トランザクションの整合性検証に成功しました。")
    else:
        print("[Validator] トランザクションの整合性検証に失敗しました。")
    # ここで生成された transaction は、DAG モジュールへ引き渡される前段階です。

if __name__ == "__main__":
    main()
