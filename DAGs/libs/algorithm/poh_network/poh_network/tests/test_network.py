# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\tests\test_network.py
import asyncio
import pytest
from poh_network.peer_manager import PeerManager
from poh_network.network import NetworkManager
from poh_storage.types import Tx


@pytest.mark.asyncio
async def test_broadcast_monkeypatch(monkeypatch):
    peers = PeerManager()
    peers.add_peer("grpc", "dummy:1")
    peers.add_peer("http", "dummy:2")
    peers.add_peer("udp", "dummy:3")

    nm = NetworkManager(peers)
    tx = Tx(tx_id="1", holder_id="h", timestamp=0.0, payload=b"p")

    # 3つの内部送信を即 True を返すフェイクに差し替え
    monkeypatch.setattr(nm, "_broadcast_grpc", lambda _tx: asyncio.sleep(0, True))
    monkeypatch.setattr(nm, "_broadcast_http", lambda _tx: asyncio.sleep(0, True))
    monkeypatch.setattr(nm, "_broadcast_udp", lambda _tx: asyncio.sleep(0, True))

    ok_grpc, ok_http, ok_udp = await nm.broadcast(tx)
    assert ok_grpc and ok_http and ok_udp
