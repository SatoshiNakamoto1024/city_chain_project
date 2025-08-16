# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\peer_manager.py
import asyncio
from typing import Dict, List, Set
import aiohttp


class PeerManager:
    """
    プロトコル別のピア一覧を保持し、
    疎通チェック（ヘルスチェック）も行えるユーティリティ。
    """

    _protocols = {"grpc", "http", "udp"}

    def __init__(self) -> None:
        self._peers: Dict[str, Set[str]] = {p: set() for p in self._protocols}

    # ---------- CRUD -------------------------------------------------

    def add_peer(self, protocol: str, address: str) -> None:
        if protocol not in self._protocols:
            raise ValueError(f"unknown protocol: {protocol}")
        self._peers[protocol].add(address)

    def remove_peer(self, protocol: str, address: str) -> None:
        self._peers.get(protocol, set()).discard(address)

    def get_peers(self, protocol: str) -> List[str]:
        return list(self._peers.get(protocol, set()))

    # ---------- health-check -----------------------------------------

    async def _check_grpc(self, address: str, timeout: float) -> bool:
        host, port = address.split(":")
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, int(port)), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _check_http(self, address: str, timeout: float) -> bool:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(address, timeout=timeout) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def _check_udp(self, address: str, timeout: float) -> bool:
        try:
            host, port = address.split(":")
            loop = asyncio.get_running_loop()
            transport, _ = await asyncio.wait_for(
                loop.create_datagram_endpoint(
                    lambda: asyncio.DatagramProtocol(), remote_addr=(host, int(port))
                ),
                timeout=timeout,
            )
            transport.close()
            return True
        except Exception:
            return False

    async def check_peer(self, protocol: str, address: str, timeout: float = 1.0) -> bool:
        if protocol == "grpc":
            return await self._check_grpc(address, timeout)
        if protocol == "http":
            return await self._check_http(address, timeout)
        if protocol == "udp":
            return await self._check_udp(address, timeout)
        raise ValueError(protocol)

    async def check_all(self, protocol: str, timeout: float = 1.0) -> Dict[str, bool]:
        peers = self.get_peers(protocol)
        tasks = {
            peer: asyncio.create_task(self.check_peer(protocol, peer, timeout))
            for peer in peers
        }
        return {peer: await task for peer, task in tasks.items()}
