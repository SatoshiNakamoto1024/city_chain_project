# \city_chain_project\network\DB\mongodb\pymongo\app.py

import asyncio
import os
import random
import string
from typing import List, Dict, Any

from motor_async_handler import MotorDBHandler


# ダミー署名（ハッシュ）
def simulate_signature(data: str) -> str:
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


async def process_transaction_batch(write_handler: MotorDBHandler, batch_data: List[Dict[str, Any]]) -> int:
    """
    1つのバッチ（暗号署名付き）を同時多発で受け取り、MongoDBに並列で書き込む。
    """
    async def do_insert(tx: Dict[str, Any]):
        # 暗号署名を付与
        signature = simulate_signature(f"{tx['sender']}{tx['receiver']}{tx['amount']}")
        tx = dict(tx)
        tx["signature"] = signature

        # 書き込み先コレクション（例：大陸ごと）
        col_name = tx.get("target_collection", "transactions")
        return await write_handler.insert_document_with_retry(col_name, tx, max_retry=5)

    tasks = [asyncio.create_task(do_insert(tx)) for tx in batch_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    return success_count


async def main():
    # === 接続情報 ===
    # 既定値はサンプル。実運用では環境変数で差し替えを推奨
    uri = os.getenv(
        "MONGODB_URL",
        "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    )
    database_name = os.getenv("MONGODB_DB", "city_chain")

    # 書き込み（プライマリ）、読み取り（セカンダリ優先）
    write_handler = await MotorDBHandler.new(uri, database_name)
    read_handler  = await MotorDBHandler.new_with_read_preference(uri, database_name)

    # 初回起動時に TTL を保証（存在すれば no-op）
    await MotorDBHandler.ensure_ttl_6months(write_handler.db["transactions"], field="createdAt")

    # (A) まず1件書き込み
    doc_single = {"user": "Alice", "action": "send", "amount": 100, "status": "pending"}
    single_id = await write_handler.insert_document("transactions", doc_single)
    print(f"[single write] Inserted ID: {single_id}")

    # (B) セカンダリ優先で読み取り
    found_doc = await read_handler.find_document("transactions", {"user": "Alice"})
    print(f"[secondary read] Found doc: {found_doc}")

    # (C) バッチ処理シナリオ（大陸っぽいコレクション名へ振り分け）
    random_batch = []
    continents = ["continent_asia", "continent_europe"]
    for i in range(10):
        sender = "User" + "".join(random.choices(string.ascii_uppercase, k=3))
        receiver = "User" + "".join(random.choices(string.ascii_uppercase, k=3))
        tx = {
            "sender": sender,
            "receiver": receiver,
            "amount": random.randint(1, 1000),
            "content": "sample content",
            "target_collection": continents[i % len(continents)],
        }
        random_batch.append(tx)

    success_count = await process_transaction_batch(write_handler, random_batch)
    print(f"[batch write] success_count={success_count}")

    # (D) セカンダリ優先で件数を確認
    for col in continents:
        await MotorDBHandler.ensure_ttl_6months(read_handler.db[col], field="createdAt")
    docs_asia = await read_handler.list_documents("continent_asia")
    docs_eu   = await read_handler.list_documents("continent_europe")
    print(f"[secondary read] continent_asia={len(docs_asia)} docs, continent_europe={len(docs_eu)} docs")

    # 終了処理
    await write_handler.close_connection()
    await read_handler.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
