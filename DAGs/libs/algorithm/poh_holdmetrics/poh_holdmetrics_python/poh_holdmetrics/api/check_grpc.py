# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\api\grpc_server.py

import asyncio
import grpc
import poh_holdmetrics.protocols.hold_pb2 as pb
import poh_holdmetrics.protocols.hold_pb2_grpc as api


async def main():
    async with grpc.aio.insecure_channel("127.0.0.1:60061") as ch:
        stub = api.HoldMetricsStub(ch)
        stream = stub.Stats(pb.google_dot_protobuf_dot_empty__pb2.Empty())
        first = await stream.read()
        print("OK holder_id=", first.holder_id, "score=", first.weighted_score)


asyncio.run(main())
