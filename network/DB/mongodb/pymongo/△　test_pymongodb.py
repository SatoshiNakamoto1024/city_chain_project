# \city_chain_project\network\DB\mongodb\pymongo\test_pymongodb.py
import os
import sys
import asyncio
import hashlib
from typing import Dict, Any
import pytest
from bson.objectid import ObjectId

# このテストファイルと同じフォルダを import path に追加
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from motor_async_handler import MotorDBHandler  # noqa: E402


# ====== 環境変数で接続情報を切り替え（本番想定） ======
URI = os.getenv(
    "MONGODB_URL",
    "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
)
DB_NAME = os.getenv("MONGODB_DB", "city_chain_pytest")
COL_BASE = os.getenv("MONGODB_COLL_BASE", "pytest_collection")


@pytest.mark.asyncio
async def test_insert_and_find_document():
    col_name = f"{COL_BASE}_basic"

    write_handler = await MotorDBHandler.new(URI, DB_NAME)
    read_handler  = await MotorDBHandler.new_with_read_preference(URI, DB_NAME)

    # TTL 6ヶ月（存在すれば no-op）
    await MotorDBHandler.ensure_ttl_6months(write_handler.db[col_name])

    # 事前掃除
    await write_handler.db[col_name].delete_many({})

    # 1) 挿入
    doc = {"user": "TestUser", "action": "test", "amount": 50, "status": "pending"}
    inserted_id = await write_handler.insert_document(col_name, doc)
    assert isinstance(inserted_id, ObjectId)

    # 2) セカンダリ優先で取得
    found = await read_handler.find_document(col_name, {"user": "TestUser"})
    assert found is not None
    assert found["user"] == "TestUser"
    assert found["amount"] == 50
    assert "createdAt" in found  # 自動付与を確認

    # 後始末
    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()


@pytest.mark.asyncio
async def test_update_document():
    col_name = f"{COL_BASE}_update"

    write_handler = await MotorDBHandler.new(URI, DB_NAME)
    read_handler  = await MotorDBHandler.new_with_read_preference(URI, DB_NAME)

    await MotorDBHandler.ensure_ttl_6months(write_handler.db[col_name])
    await write_handler.db[col_name].delete_many({})

    await write_handler.insert_document(col_name, {"user": "U1", "action": "t", "amount": 50, "status": "pending"})
    updated = await write_handler.update_document(col_name, {"user": "U1"}, {"amount": 100})
    assert updated == 1

    got = await read_handler.find_document(col_name, {"user": "U1"})
    assert got is not None and got["amount"] == 100

    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()


@pytest.mark.asyncio
async def test_delete_document():
    col_name = f"{COL_BASE}_delete"

    write_handler = await MotorDBHandler.new(URI, DB_NAME)
    read_handler  = await MotorDBHandler.new_with_read_preference(URI, DB_NAME)

    await MotorDBHandler.ensure_ttl_6months(write_handler.db[col_name])
    await write_handler.db[col_name].delete_many({})

    await write_handler.insert_document(col_name, {"user": "U1", "action": "t", "amount": 50, "status": "pending"})
    deleted = await write_handler.delete_document(col_name, {"user": "U1"})
    assert deleted == 1

    got = await read_handler.find_document(col_name, {"user": "U1"})
    assert got is None

    await write_handler.close_connection()
    await read_handler.close_connection()


@pytest.mark.asyncio
async def test_list_documents():
    col_name = f"{COL_BASE}_list"

    write_handler = await MotorDBHandler.new(URI, DB_NAME)
    read_handler  = await MotorDBHandler.new_with_read_preference(URI, DB_NAME)

    await MotorDBHandler.ensure_ttl_6months(write_handler.db[col_name])
    await write_handler.db[col_name].delete_many({})

    await write_handler.insert_document(col_name, {"user": "A", "action": "t", "amount": 50, "status": "pending"})
    await write_handler.insert_document(col_name, {"user": "B", "action": "t", "amount": 30, "status": "pending"})

    all_docs = await read_handler.list_documents(col_name)
    users = {d["user"] for d in all_docs}
    assert {"A", "B"} <= users

    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()


@pytest.mark.asyncio
async def test_parallel_inserts():
    """
    高並列挿入 + 署名付与 + セカンダリ読み取り確認。
    """
    col_name = f"{COL_BASE}_batch"

    write_handler = await MotorDBHandler.new(URI, DB_NAME)
    read_handler  = await MotorDBHandler.new_with_read_preference(URI, DB_NAME)

    await MotorDBHandler.ensure_ttl_6months(write_handler.db[col_name])
    await write_handler.db[col_name].delete_many({})

    def sign(d: Dict[str, Any]) -> str:
        s = f"{d['user']}{d['amount']}"
        return hashlib.sha256(s.encode()).hexdigest()

    async def insert_one(i: int):
        doc = {"user": f"User_{i}", "action": "send", "amount": i * 10, "status": "pending"}
        doc["signature"] = sign(doc)
        return await write_handler.insert_document(col_name, doc)

    tasks = [asyncio.create_task(insert_one(i)) for i in range(50)]
    res = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(not isinstance(x, Exception) for x in res)

    all_docs = await read_handler.list_documents(col_name)
    assert len(all_docs) == 50

    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()
