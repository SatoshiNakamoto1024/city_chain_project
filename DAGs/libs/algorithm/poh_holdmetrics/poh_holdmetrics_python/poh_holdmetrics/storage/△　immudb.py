# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\storage\immudb.py
import grpc
import json
from datetime import datetime
from ..config import settings
from ..data_models import HoldEvent, HoldStat
from poh_holdmetrics.protocols import immudb_pb2 as immu_pb
from poh_holdmetrics.protocols import immudb_pb2_grpc as immu_grpc

class ImmudbStorage:
    """
    immuDB 非同期ストレージプラグイン (gRPC)。
    Key=holder_id:timestamp, Value=JSON(event) を保存し
    Scan で全件取得して集計します。
    """
    def __init__(self):
        if not settings.immudb_url:
            raise RuntimeError("IMMUDB_URL が設定されていません")
        channel = grpc.aio.insecure_channel(settings.immudb_url)
        self.client = immu_grpc.ImmuServiceStub(channel)

    async def save_event(self, event: HoldEvent):
        key = f"{event.holder_id}:{int(event.start.timestamp())}".encode()
        val = json.dumps(event.dict()).encode()
        await self.client.Set(immu_pb.KV(key=key, value=val))

    async def get_stats(self) -> list[HoldStat]:
        req = immu_pb.ScanRequest(prefix=b"", limit=0)
        resp = await self.client.Scan(req)
        stats: dict[str, float] = {}
        for kv in resp.kvs:
            raw = json.loads(kv.value)
            ev = HoldEvent.parse_obj(raw)
            st = ev.start
            ed = ev.end or datetime.utcnow()
            dur = (ed - st).total_seconds() * ev.weight
            stats.setdefault(ev.holder_id, 0.0)
            stats[ev.holder_id] += dur
        return [HoldStat(holder_id=k, weighted_score=v) for k, v in stats.items()]
