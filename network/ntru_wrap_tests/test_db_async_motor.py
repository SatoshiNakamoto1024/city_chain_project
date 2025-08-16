# network/tests/test_db_async_motor.py
from __future__ import annotations
import asyncio
import os
import pytest
import pytest_asyncio
from bson import ObjectId

# Motor ラッパはフルパス import
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from network.DB.mongodb.pymongo.motor_async_handler import MotorDBHandler

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="function")
async def motor_handlers(mongo_uri: str, mongo_dbname: str):
    mongo_uri = "mongodb://localhost:27017/"  # レプリカセットなし
    mongo_dbname = "unit_test_db"
    write = await MotorDBHandler.new(mongo_uri, mongo_dbname)
    read  = await MotorDBHandler.new_with_read_preference(mongo_uri, mongo_dbname)
    yield write, read
    await write.close_connection()
    await read.close_connection()

async def test_motor_insert_and_read(motor_handlers):
    write, read = motor_handlers
    col = "motor_test"

    # 前掃除
    await write.db[col].delete_many({})  # type: ignore[attr-defined]

    # insert
    _id = await write.insert_document(col, {"user": "Bob", "content": "秘密メモ", "amount": 123})
    assert isinstance(_id, ObjectId)

    # read
    doc = await read.find_document(col, {"_id": _id})
    assert doc["user"] == "Bob"
    assert doc["amount"] == 123
    # 「content」が透過的に復号されているか
    assert doc["content"] == "秘密メモ"
