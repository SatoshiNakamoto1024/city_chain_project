# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\grpc_server.py
import logging

import grpc.aio

from poh_storage.storage import StorageManager
from poh_storage.types import Tx
from .protocols import poh_pb2, poh_pb2_grpc

logging.basicConfig(level=logging.INFO)


class PohService(poh_pb2_grpc.PohServiceServicer):
    def __init__(self, storage: StorageManager):
        self._storage = storage

    async def Broadcast(self, request, context):
        tx = Tx(
            tx_id=request.tx_id,
            holder_id=request.holder_id,
            timestamp=request.timestamp,
            payload=request.payload,
        )
        await self._storage.save_tx(tx)
        return poh_pb2.Ack(success=True)


async def serve(port: int, base_dir: str, db_path: str):
    """
    非同期 gRPC サーバを起動して待機し続ける。
    シグナル等でキャンセルされたら自然に終了。
    """
    server = grpc.aio.server()
    storage = await StorageManager.create(base_dir, db_path)
    poh_pb2_grpc.add_PohServiceServicer_to_server(PohService(storage), server)
    server.add_insecure_port(f"0.0.0.0:{port}")
    await server.start()
    logging.info("gRPC listening on :%d", port)
    await server.wait_for_termination()
