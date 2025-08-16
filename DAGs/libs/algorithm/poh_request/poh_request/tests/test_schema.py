# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\tests\test_schema.py
from datetime import datetime, timezone

import pytest

from poh_request.schema import PoHRequest, PoHResponse


def test_request_valid():
    now = datetime.now(timezone.utc)
    req = PoHRequest(
        token_id="TK",
        holder_id="H",
        amount=1,
        nonce=1,
        created_at=now,
    )
    assert req.created_at == now


def test_request_invalid_amount():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PoHRequest(
            token_id="TK",
            holder_id="H",
            amount=0,
            nonce=1,
            created_at=datetime.now(timezone.utc),
        )


def test_response_valid():
    resp = PoHResponse(
        txid="X",
        status="accepted",
        received_at=datetime.now(timezone.utc),
    )
    assert resp.status == "accepted"


def test_response_invalid_status():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PoHResponse(
            txid="X",
            status="oops",
            received_at=datetime.now(timezone.utc),
        )
