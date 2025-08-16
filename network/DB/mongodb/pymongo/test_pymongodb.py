# D:\city_chain_project\network\DB\mongodb\pymongo\test_pymongodb.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import asyncio
from motor_async_handler import MotorDBHandler
from bson.objectid import ObjectId

@pytest.mark.asyncio
async def test_insert_and_find_document():
    uri = "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name = "test_async_db"
    col_name = "test_async_collection"

    # 書き込み用（プライマリ）
    write_handler = await MotorDBHandler.new(uri, db_name)
    # テスト用: 事前に削除
    await write_handler.db[col_name].delete_many({})

    doc = {
        "user": "TestUser",
        "action": "test",
        "amount": 50,
        "status": "pending"
    }
    inserted_id = await write_handler.insert_document(col_name, doc)
    assert isinstance(inserted_id, ObjectId)

    # 読み取り用（セカンダリ優先）
    read_handler = await MotorDBHandler.new_with_read_preference(uri, db_name)
    found_doc = await read_handler.find_document(col_name, {"user": "TestUser"})
    assert found_doc is not None
    assert found_doc["user"] == "TestUser"
    assert found_doc["amount"] == 50

    # 後処理
    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()

@pytest.mark.asyncio
async def test_update_document():
    uri = "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name = "test_async_db"
    col_name = "test_async_collection"

    write_handler = await MotorDBHandler.new(uri, db_name)
    await write_handler.db[col_name].delete_many({})

    doc = {"user": "TestUser", "action": "test", "amount": 50, "status": "pending"}
    await write_handler.insert_document(col_name, doc)

    updated_count = await write_handler.update_document(col_name, {"user": "TestUser"}, {"amount": 100})
    assert updated_count == 1

    # 読み取り(セカンダリ)
    read_handler = await MotorDBHandler.new_with_read_preference(uri, db_name)
    found_doc = await read_handler.find_document(col_name, {"user": "TestUser"})
    assert found_doc is not None
    assert found_doc["amount"] == 100

    # 後処理
    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()

@pytest.mark.asyncio
async def test_delete_document():
    uri = "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name = "test_async_db"
    col_name = "test_async_collection"

    write_handler = await MotorDBHandler.new(uri, db_name)
    await write_handler.db[col_name].delete_many({})

    doc = {"user": "TestUser", "action": "test", "amount": 50, "status": "pending"}
    await write_handler.insert_document(col_name, doc)

    deleted_count = await write_handler.delete_document(col_name, {"user": "TestUser"})
    assert deleted_count == 1

    read_handler = await MotorDBHandler.new_with_read_preference(uri, db_name)
    found_doc = await read_handler.find_document(col_name, {"user": "TestUser"})
    assert found_doc is None

    await write_handler.close_connection()
    await read_handler.close_connection()

@pytest.mark.asyncio
async def test_list_documents():
    uri = "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name = "test_async_db"
    col_name = "test_async_collection"

    write_handler = await MotorDBHandler.new(uri, db_name)
    await write_handler.db[col_name].delete_many({})

    await write_handler.insert_document(col_name, {"user": "TestUser", "action": "test", "amount": 50, "status": "pending"})
    await write_handler.insert_document(col_name, {"user": "AnotherUser", "action": "test", "amount": 30, "status": "pending"})

    read_handler = await MotorDBHandler.new_with_read_preference(uri, db_name)
    all_docs = await read_handler.list_documents(col_name)
    assert len(all_docs) == 2

    users = [doc["user"] for doc in all_docs]
    assert "TestUser" in users
    assert "AnotherUser" in users

    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()

@pytest.mark.asyncio
async def test_parallel_inserts():
    """
    高並列の挿入テスト。暗号署名入りのドキュメントを複数生成し、同時に挿入。
    """
    uri = "mongodb+srv://satoshi:greg1024@cluster0.6gb92.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name = "test_async_db"
    col_name = "test_batch"

    write_handler = await MotorDBHandler.new(uri, db_name)
    read_handler = await MotorDBHandler.new_with_read_preference(uri, db_name)
    await write_handler.db[col_name].delete_many({})

    import hashlib
    def sign_document(d):
        s = f"{d['user']}{d['amount']}"
        return hashlib.sha256(s.encode()).hexdigest()

    async def insert_task(doc):
        # 暗号署名を付与
        doc["signature"] = sign_document(doc)
        return await write_handler.insert_document(col_name, doc)

    docs_to_insert = []
    for i in range(50):
        docs_to_insert.append({
            "user": f"User_{i}",
            "action": "send",
            "amount": i * 10,
            "status": "pending"
        })

    # 並列に挿入
    tasks = [asyncio.create_task(insert_task(d)) for d in docs_to_insert]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception))
    assert success_count == 50

    # セカンダリ優先で件数を確認
    all_docs = await read_handler.list_documents(col_name)
    assert len(all_docs) == 50

    # 後処理
    await write_handler.db[col_name].delete_many({})
    await write_handler.close_connection()
    await read_handler.close_connection()
