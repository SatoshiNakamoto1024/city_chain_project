
import asyncio
from object_processing.router import Router
from object_processing.shard_worker import ShardWorker

async def main():
    router = Router()
    await router.start()

    # 各シャードワーカーを起動
    for i, q in enumerate(router.queues):
        w = ShardWorker(i, q)
        await w.start()

    # 以下、gRPC や HTTP で来るイベントを router.ingress.put(evt) で投入
    # 例:
    # while True:
    #     evt = await receive_event()
    #     await router.ingress.put(evt)

if __name__ == "__main__":
    asyncio.run(main())
