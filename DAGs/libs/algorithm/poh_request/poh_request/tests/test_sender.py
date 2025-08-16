# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\tests\test_sender.py
import asyncio
import json

import httpx
import pytest
from httpx import MockTransport, Request, Response

from poh_request.exceptions import SendError
from poh_request.schema import PoHResponse
from poh_request.sender import AsyncSender, send_sync


@pytest.mark.asyncio
async def test_async_sender_success(monkeypatch):
    data = {
        "txid": "TX123",
        "status": "accepted",
        "received_at": "2025-01-01T00:00:00Z",
        "reason": None,
    }

    def handler(request: Request):
        return Response(200, json=data)

    client = httpx.AsyncClient(transport=MockTransport(handler))
    monkeypatch.setattr("poh_request.sender.httpx.AsyncClient", lambda **_: client)

    resp = await AsyncSender().send("payload")
    assert resp.txid == "TX123"


@pytest.mark.asyncio
async def test_async_sender_http_error(monkeypatch):
    def handler(request: Request):
        return Response(500, text="error")

    client = httpx.AsyncClient(transport=MockTransport(handler))
    monkeypatch.setattr("poh_request.sender.httpx.AsyncClient", lambda **_: client)

    with pytest.raises(SendError):
        await AsyncSender().send("p")


def test_send_sync(monkeypatch):
    dummy = PoHResponse(
        txid="Q", status="queued", received_at="2025-01-01T00:00:00Z"
    )
    monkeypatch.setattr(
        "poh_request.sender.AsyncSender.send",
        lambda *_: asyncio.get_event_loop().create_future().set_result(dummy) or dummy,
    )
    out = send_sync("p")
    assert out.status == "queued"
