# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\udp_listener.py
import asyncio
import logging

from poh_storage.storage import StorageManager
from poh_storage.types   import Tx

logging.basicConfig(level=logging.INFO)


class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, storage: StorageManager):
        self._storage = storage

    def datagram_received(self, data: bytes, addr):
        tx = Tx(
            tx_id=f"{addr}",
            holder_id=f"{addr}",
            timestamp=asyncio.get_event_loop().time(),
            payload=data,
        )
        asyncio.create_task(self._storage.save_tx(tx))
        logging.debug("UDP received from %s", addr)


async def listen_udp(port: int, base_dir: str, db_path: str):
    """
    指定ポートで UDP を非同期受信し続ける。
    """
    loop = asyncio.get_running_loop()
    storage = await StorageManager.create(base_dir, db_path)
    await loop.create_datagram_endpoint(
        lambda: _UDPProtocol(storage), local_addr=("0.0.0.0", port)
    )
    logging.info("UDP listener on :%d", port)
    await asyncio.Event().wait()
