# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\network.py
import asyncio
from typing import List

import aiohttp
import grpc.aio

from poh_storage.types import Tx
from .peer_manager import PeerManager
from .protocols import poh_pb2, poh_pb2_grpc


class _UDPSender(asyncio.DatagramProtocol):
    """単発送信用 DatagramProtocol"""

    def __init__(self, data: bytes):
        self._data = data

    def connection_made(self, transport):
        transport.sendto(self._data)
        transport.close()


class NetworkManager:
    """
    PoH Tx を gRPC / HTTP / UDP で並列送信する高レベル API。
    """

    def __init__(self, peers: PeerManager):
        self._peers = peers

    # ---------- public ----------

    async def broadcast(self, tx: Tx) -> List[bool]:
        """
        3プロトコルに同時ブロードキャストし、[grpc_ok, http_ok, udp_ok] を返す。
        どれか1つでも True なら “ある程度” 配信成功とみなせる。
        """
        send_tasks = (
            self._broadcast_grpc(tx),
            self._broadcast_http(tx),
            self._broadcast_udp(tx),
        )
        return await asyncio.gather(*send_tasks)

    # ---------- internal : gRPC ----------

    async def _send_grpc_single(self, endpoint: str, tx: Tx) -> bool:
        async with grpc.aio.insecure_channel(endpoint) as channel:
            stub = poh_pb2_grpc.PohServiceStub(channel)
            req = poh_pb2.Tx(
                tx_id=tx.tx_id,
                holder_id=tx.holder_id,
                timestamp=tx.timestamp,
                payload=tx.payload,
            )
            try:
                ack = await stub.Broadcast(req, timeout=1.0)
                return ack.success
            except Exception:
                return False

    async def _broadcast_grpc(self, tx: Tx) -> bool:
        peers = self._peers.get_peers("grpc")
        if not peers:
            return False
        results = await asyncio.gather(
            *[self._send_grpc_single(p, tx) for p in peers], return_exceptions=False
        )
        return any(results)

    # ---------- internal : HTTP ----------

    async def _broadcast_http(self, tx: Tx) -> bool:
        peers = self._peers.get_peers("http")
        if not peers:
            return False
        async with aiohttp.ClientSession() as sess:
            tasks = [
                sess.post(f"{peer}/broadcast", json=tx.__dict__, timeout=1.0)
                for peer in peers
            ]
            try:
                resps = await asyncio.gather(*tasks, return_exceptions=True)
                return any(r.status == 200 for r in resps if isinstance(r, aiohttp.ClientResponse))
            except Exception:
                return False

    # ---------- internal : UDP ----------

    async def _broadcast_udp(self, tx: Tx) -> bool:
        peers = self._peers.get_peers("udp")
        loop = asyncio.get_running_loop()
        tasks = []
        for peer in peers:
            host, port = peer.split(":")
            coro = loop.create_datagram_endpoint(
                lambda: _UDPSender(tx.payload), remote_addr=(host, int(port))
            )
            tasks.append(coro)
        if not tasks:
            return False
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
            return True
        except Exception:
            return False
