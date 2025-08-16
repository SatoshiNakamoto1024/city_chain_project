# D:\city_chain_project\network\DB\mongodb\pymongo\app.py

import asyncio
import random
import string
import time
from motor_async_handler import MotorDBHandler

# 暗号署名を模擬する関数
def simulate_signature(data: str) -> str:
    # 実際にはRSA/ECDSAなどを使うが、ここでは簡単に sha256 的なのを模擬
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()

async def process_transaction_batch(write_handler: MotorDBHandler, batch_data: list):
    """
    1つのバッチ（暗号署名付き）を同時多発的に受け取り、MongoDBに並列で書き込む例。
    """
    tasks = []
    for tx in batch_data:
        # tx: {"sender": ..., "receiver": ..., "amount": ..., "content": ...}
        # 暗号署名を付与
        signature = simulate_signature(f"{tx['sender']}{tx['receiver']}{tx['amount']}")
        tx["signature"] = signature

        # 送信先コレクションを決める（例：大陸 or 市町村など）
        col_name = tx.get("target_collection", "default_collection")

        tasks.append(write_handler.insert_document(col_name, tx))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    return success_count

async def main():
    uri = "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "async_test_db"

    # 書き込み用（プライマリ）ハンドラ
    write_handler = await MotorDBHandler.new(uri, database_name)
    # 読み取り用（セカンダリ優先）ハンドラ
    read_handler = await MotorDBHandler.new_with_read_preference(uri, database_name)

    # (A) まず単純に1件書き込み
    doc_single = {
        "user": "Alice",
        "action": "send",
        "amount": 100,
        "status": "pending"
    }
    single_id = await write_handler.insert_document("transactions", doc_single)
    print(f"[single write] Inserted ID: {single_id}")

    # (B) セカンダリから読み取る
    found_doc = await read_handler.find_document("transactions", {"user": "Alice"})
    print(f"[secondary read] Found doc: {found_doc}")

    # (C) バッチ処理シナリオ
    # 同時多発で暗号署名入りのトランザクションが発生する想定
    random_batch = []
    for i in range(10):
        # ダミーデータ
        sender = "User" + "".join(random.choices(string.ascii_uppercase, k=3))
        receiver = "User" + "".join(random.choices(string.ascii_uppercase, k=3))
        tx = {
            "sender": sender,
            "receiver": receiver,
            "amount": random.randint(1, 1000),
            "content": "sample content",
            "target_collection": "continent_asia" if i % 2 == 0 else "continent_europe"
        }
        random_batch.append(tx)

    success_count = await process_transaction_batch(write_handler, random_batch)
    print(f"[batch write] success_count={success_count}")

    # (D) 書き込み後、セカンダリ優先で continent_asia の件数を確認
    docs_asia = await read_handler.list_documents("continent_asia")
    docs_eu = await read_handler.list_documents("continent_europe")
    print(f"[secondary read] continent_asia has {len(docs_asia)} docs, continent_europe has {len(docs_eu)} docs")

    # 終了時にコネクションを閉じる
    await write_handler.close_connection()
    await read_handler.close_connection()

if __name__ == "__main__":
    asyncio.run(main())
