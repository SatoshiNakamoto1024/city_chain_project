import grpc
from grpc_dag.gen.dag_pb2 import PoHRequest, PoHResponse
from grpc_dag.gen.dag_pb2_grpc import DAGServiceStub


class PoHResponse:
    def __init__(self, success: bool, holder_id: str, signature: str):
        self.success = success
        self.holder_id = holder_id
        self.signature = signature


async def send_poh_request(
    endpoint: str,
    tx_id: str,
    payload: str,
    timeout: float
) -> PoHResponse:
    """
    指定ノードの gRPC サーバーに PoH_REQUEST を送信
    """
    async with grpc.aio.insecure_channel(endpoint) as chan:
        stub = DAGServiceStub(chan)
        req = PoHRequest(tx_id=tx_id, payload=payload)
        resp = await stub.PoHRequest(req, timeout=timeout)
        return PoHResponse(
            success=(resp.status == "OK"),
            holder_id=resp.holder_id,
            signature=resp.signature
        )
