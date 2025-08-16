# sending_dapps/sending_dapps.py
"""
sending_dapps.py

このモジュールは、send_screen.html などから受信したトランザクション情報を統合し、
以下の一連の処理を実施します。

1. ユーザー認証（JWT検証）およびユーザー情報の取得
2. 入力データの必須項目検証
3. 暗号処理：
   - NTRU によるメッセージ暗号化
   - RSA によるウォレット情報の暗号化
   - Dilithium による署名生成
4. トランザクションデータの統合（各フィールドの整合性検証含む）
5. 統合トランザクションを DAG システムへ非同期に送信

※ ユーザー認証・管理は auth_py や user_manager、session_manager などの各モジュールを利用する想定です。
"""

import json
import uuid
import time
from datetime import datetime, timezone
import asyncio
import logging

# ユーザー認証・管理モジュール（各パッケージはすでに実装済みとする）
from auth_py.jwt_manager import verify_jwt
from user_manager.user_db import get_user
# （必要に応じてセッション管理も取り入れる： from session_manager.session_service import ...）

# 暗号処理モジュール
from auth_py.crypto import ntru, rsa, dilithium

# DAG 連携
from dag.dag_handler import DAGHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

async def process_sending_transaction(data: dict, jwt_token: str) -> dict:
    """
    ユーザー認証済みの状態（JWT検証済み）で、send_screen.html から送信されたトランザクション情報を処理し、
    暗号処理と署名を行った後、DAG へ非同期に登録します。

    Args:
        data (dict): トランザクション入力データ
        jwt_token (str): ユーザー認証用 JWT トークン

    Returns:
        dict: 最終的に統合されたトランザクションデータ
    """
    # 1) JWT 検証
    try:
        payload = verify_jwt(jwt_token)
    except Exception as e:
        raise Exception(f"JWT検証失敗: {e}")
    
    user_uuid = payload.get("uuid")
    if not user_uuid:
        raise Exception("JWTにユーザーIDが含まれていません")
    
    # 2) ユーザー情報の取得
    user = get_user(user_uuid)
    if not user:
        raise Exception("ユーザー情報が見つかりません")
    
    # 3) 必須フィールドの検証
    required_fields = [
        "sender", "receiver", "sender_wallet", "receiver_wallet", "amount",
        "message", "verifiable_credential", "subject", "action_level", "dimension",
        "fluctuation", "organism_name", "sender_municipality", "receiver_municipality",
        "details", "goods_or_money", "location", "proof_of_place", "attributes"
    ]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"必須フィールドが不足しています: {field}")
    
    # ※ ユーザー情報の整合性チェック（例: data["sender"] が user.name と一致するかなど）
    # ここではシンプルな警告のみを出力
    if data["sender"] != user.name:
        logger.warning("送信者情報がログインユーザーと一致しません (入力: %s, DB: %s)", data["sender"], user.name)
    
    # 4) タイムスタンプとトランザクションIDの設定
    timestamp = datetime.now(timezone.utc).isoformat() + "Z"
    transaction_id = str(uuid.uuid4())
    
    # 5) 暗号処理
    encrypted_message = ntru.encrypt(data["message"], public_key="ntru_public_key_dummy")
    encrypted_sender_wallet = rsa.encrypt(data["sender_wallet"], public_key="rsa_public_key_dummy")
    encrypted_receiver_wallet = rsa.encrypt(data["receiver_wallet"], public_key="rsa_public_key_dummy")
    
    # 6) 署名生成（対象はトランザクションの基本情報）
    tx_payload = {
        "transaction_id": transaction_id,
        "sender": data["sender"],
        "receiver": data["receiver"],
        "amount": float(data["amount"]),
        "timestamp": timestamp,
        "subject": data["subject"],
        "details": data["details"]
    }
    payload_bytes = json.dumps(tx_payload, sort_keys=True).encode('utf-8')
    dummy_private_key = b"dummy_private_key_for_dilithium"
    signature = dilithium.sign(payload_bytes, dummy_private_key)
    
    # 7) 統合トランザクションデータの作成
    transaction = {
        "sender": data["sender"],
        "receiver": data["receiver"],
        "to_wallet": encrypted_receiver_wallet,
        "from_wallet": encrypted_sender_wallet,
        "amount": float(data["amount"]),
        "timestamp": timestamp,
        "transaction_id": transaction_id,
        "verifiable_credential": data["verifiable_credential"],
        "signature": signature,
        "pq_public_key": "dummy_pq_public_key",  # 実際はユーザーの公開鍵など
        "subject": data["subject"],
        "action_level": data["action_level"],
        "dimension": data["dimension"],
        "fluctuation": data["fluctuation"],
        "organism_name": data["organism_name"],
        "sender_municipality": data["sender_municipality"],
        "receiver_municipality": data["receiver_municipality"],
        "sender_municipal_id": data["sender_municipality"],  # 仮
        "receiver_municipal_id": data["receiver_municipality"],  # 仮
        "details": data["details"],
        "goods_or_money": data["goods_or_money"],
        "location": data["location"],
        "proof_of_place": data["proof_of_place"],
        "status": "send_complete",
        "created_at": timestamp,
        "attributes": data["attributes"],
        "encrypted_message": encrypted_message,
        "transaction_hash": "dummy_tx_hash",  # 本来はハッシュ計算
        "sender_representative": "",  # DPoS 等の処理で決定
        "receiver_representative": ""  # DPoS 等の処理で決定
    }
    
    logger.info("[SendingDApps] 統合トランザクション:\n%s", json.dumps(transaction, indent=2, ensure_ascii=False))
    
    # 8) DAG への登録（非同期呼び出し）
    handler = DAGHandler(batch_interval=1)
    tx_id_dag, tx_hash = await handler.add_transaction(
        transaction["sender"], transaction["receiver"], transaction["amount"], tx_type="send"
    )
    transaction["transaction_id"] = tx_id_dag
    transaction["transaction_hash"] = tx_hash
    logger.info("[SendingDApps] DAG 登録完了: tx_id=%s, tx_hash=%s", tx_id_dag, tx_hash)
    
    return transaction

# ============================
# テスト実行部
# ============================
if __name__ == "__main__":
    import asyncio
    sample_data = {
        "sender": "User1",
        "receiver": "User11",
        "sender_wallet": "user1_wallet",
        "receiver_wallet": "user11_wallet",
        "amount": "150.75",
        "message": "Payment message 1",
        "verifiable_credential": "credential_1",
        "subject": "Payment",
        "action_level": "high",
        "dimension": "global",
        "fluctuation": "none",
        "organism_name": "TestOrg",
        "sender_municipality": "CityA",
        "receiver_municipality": "CityD",
        "details": "Payment for service 1",
        "goods_or_money": "money",
        "location": "Tokyo",
        "proof_of_place": "GPS_data",
        "attributes": {"priority": "urgent"}
    }
    
    async def test_sending():
        # ダミーの JWT トークン（実際にはログイン済みユーザーから発行される有効なトークンを使用）
        dummy_jwt = "dummy_jwt_token_that_should_be_valid"
        try:
            result = await process_sending_transaction(sample_data, dummy_jwt)
            print("=== 最終統合トランザクション ===")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print("エラー:", e)
    
    asyncio.run(test_sending())
