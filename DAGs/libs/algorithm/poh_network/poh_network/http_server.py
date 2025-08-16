# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\http_server.py
import asyncio
import logging
from aiohttp import web

from poh_storage.storage import StorageManager
from poh_storage.types   import Tx

logging.basicConfig(level=logging.INFO)


async def handle_broadcast(request: web.Request) -> web.Response:
    data = await request.json()
    tx = Tx(
        tx_id=data["tx_id"],
        holder_id=data["holder_id"],
        timestamp=data["timestamp"],
        payload=bytes(data["payload"], "latin1"),
    )
    storage: StorageManager = request.app["storage"]
    await storage.save_tx(tx)
    return web.Response(text="OK")


async def create_app(base_dir: str, db_path: str) -> web.Application:
    app = web.Application()
    storage = await StorageManager.create(base_dir, db_path)
    app["storage"] = storage
    app.router.add_post("/broadcast", handle_broadcast)
    return app


async def run_http_server(port: int, base_dir: str, db_path: str):
    app = await create_app(base_dir, db_path)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("HTTP server listening on :%d", port)
    await asyncio.Event().wait()  # Ctrl-C で終了
