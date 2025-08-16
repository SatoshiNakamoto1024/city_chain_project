# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\tests\test_builder.py
import json
import hashlib
from datetime import datetime, timezone

import pytest
from nacl import signing
from nacl.encoding import RawEncoder

from poh_request.builder import PoHRequestBuilder
from poh_request.exceptions import EncodeError
from poh_request.utils import b58decode


def _digest_no_sig(builder: PoHRequestBuilder) -> bytes:
    data = builder.request.model_dump(exclude={"signature"})
    return hashlib.sha256(json.dumps(data, separators=(",", ":")).encode()).digest()


def test_builder_sign_and_encode():
    sk = signing.SigningKey.generate()
    builder = PoHRequestBuilder(
        sk,
        token_id="TK",
        holder_id="H",
        amount=42,
        nonce=7,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    ).sign()

    sig_b58 = builder.request.signature
    assert sig_b58

    # verify
    vk = sk.verify_key
    vk.verify(_digest_no_sig(builder), b58decode(sig_b58), encoder=RawEncoder)

    # encode round‑trip
    payload = builder.encode()
    decoded = json.loads(b58decode(payload))
    assert decoded["token_id"] == "TK"
    assert decoded["signature"] == sig_b58


def test_builder_sign_failure(monkeypatch):
    sk = signing.SigningKey.generate()
    builder = PoHRequestBuilder(sk, token_id="T", holder_id="H", amount=1)

    # break hashlib.sha256
    monkeypatch.setattr(
        "poh_request.builder.hashlib.sha256",
        lambda *_: (_ for _ in ()).throw(ValueError("fail")),
    )
    with pytest.raises(EncodeError):
        builder.sign()
