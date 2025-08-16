# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\tests\test_verifier.py
# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\tests\test_verifier.py
import pytest
import asyncio
from datetime import datetime, timezone, timedelta

import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from poh_ack.models import AckRequest
from poh_ack.verifier import verify_ack, verify_ack_async


def make_test_ack(timestamp: str) -> AckRequest:
    """
    テスト用に Ed25519 キーペア生成し、
    canonical payload を署名して AckRequest を返す
    """
    sk = Ed25519PrivateKey.generate()
    vk = sk.public_key()
    payload = f'{{"id":"id1","timestamp":"{timestamp}"}}'.encode("utf-8")
    sig = sk.sign(payload)

    # 公開鍵を raw bytes にエンコード
    pk_bytes = vk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return AckRequest(
        id="id1",
        timestamp=timestamp,
        signature=base58.b58encode(sig).decode(),
        pubkey=base58.b58encode(pk_bytes).decode(),
    )


def test_verify_sync_valid():
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack(now)
    res = verify_ack(req, ttl_seconds=60)
    assert res.valid and res.error is None


def test_verify_sync_ttl_expired():
    old = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    req = make_test_ack(old)
    res = verify_ack(req, ttl_seconds=30)
    assert not res.valid
    assert "TTL" in (res.error or "")


@pytest.mark.asyncio
async def test_verify_async_valid():
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack(now)
    res = await verify_ack_async(req, ttl_seconds=60)
    assert res.valid and res.error is None


@pytest.mark.asyncio
async def test_verify_async_ttl_expired():
    old = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    req = make_test_ack(old)
    res = await verify_ack_async(req, ttl_seconds=30)
    assert not res.valid
    assert "TTL" in (res.error or "")
