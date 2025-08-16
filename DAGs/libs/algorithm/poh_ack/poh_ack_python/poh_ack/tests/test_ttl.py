# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\tests\test_ttl.py

import pytest
from datetime import datetime, timezone, timedelta

import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from poh_ack.models import AckRequest
from poh_ack.verifier import _verify_fallback  # private ですがテスト用に直接呼び出します


def make_test_ack(timestamp: str) -> AckRequest:
    """
    テスト用に Ed25519 キーペアを生成し、
    canonical payload を署名して AckRequest を返す
    """
    sk = Ed25519PrivateKey.generate()
    vk = sk.public_key()
    payload = f'{{"id":"x","timestamp":"{timestamp}"}}'.encode("utf-8")
    sig = sk.sign(payload)
    # 公開鍵を raw bytes にエンコード
    pk_bytes = vk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return AckRequest(
        id="x",
        timestamp=timestamp,
        signature=base58.b58encode(sig).decode(),
        pubkey=base58.b58encode(pk_bytes).decode(),
    )


def test_ttl_valid():
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack(now)
    res = _verify_fallback(req, ttl_seconds=60)
    assert res.valid


def test_ttl_expired():
    old = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    req = make_test_ack(old)
    res = _verify_fallback(req, ttl_seconds=30)
    assert not res.valid
    assert "TTL" in (res.error or "")
