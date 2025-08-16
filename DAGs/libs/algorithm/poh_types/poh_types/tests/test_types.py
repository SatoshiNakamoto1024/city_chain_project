# D:\city_chain_project\DAGs\libs\algorithm\poh_types\poh_types\tests\test_types.py
import pytest
import json
import time

from poh_types.types import PoHTx, PoHReq, PoHAck
from poh_types.exceptions import PoHTypesError

def test_base_post_init():
    now = time.time()
    tx = PoHTx(tx_id="tx1", holder_id="nodeA", timestamp=now)
    assert tx.tx_id == "tx1"
    assert isinstance(tx.to_json(), str)

def test_from_json_sync():
    data = {"tx_id":"tx2","holder_id":"nodeB","timestamp":123.0}
    text = json.dumps(data)
    tx = PoHTx.from_json(text)
    assert tx.tx_id == "tx2"

def test_validate_timestamp_ok():
    tx = PoHTx(tx_id="x", holder_id="h", timestamp=time.time())
    # 同期版でも例外なし
    # 非同期版
    import asyncio
    asyncio.run(tx.validate_timestamp(allow_drift=5.0))

def test_validate_timestamp_fail():
    old = time.time() - 10.0
    tx = PoHTx(tx_id="x", holder_id="h", timestamp=old)
    import asyncio
    with pytest.raises(PoHTypesError):
        asyncio.run(tx.validate_timestamp(allow_drift=1.0))

def test_pohreq_inherits_pohtx():
    now = time.time()
    req = PoHReq(tx_id="a", holder_id="b", timestamp=now)
    assert isinstance(req, PoHTx)

def test_po_hack_required_fields():
    now = time.time()
    with pytest.raises(PoHTypesError):
        PoHAck(tx_id="a", holder_id="b", timestamp=now,
               storage_hash="", sig_alg="alg", signature="sig")

    ack = PoHAck(tx_id="a", holder_id="b", timestamp=now, storage_hash="abcd", sig_alg="alg", signature="sig")
    # 非同期シリアライズもエラーなし
    import asyncio
    text = asyncio.run(ack.to_json_async())
    assert '"storage_hash":"abcd"' in text
