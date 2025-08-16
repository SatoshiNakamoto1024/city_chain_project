# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\tests\test_udp_listener.py
import asyncio
import pytest
from poh_network.udp_listener import listen_udp
from contextlib import suppress


@pytest.mark.asyncio
async def test_udp_listener(tmp_path, unused_udp_port):
    base = str(tmp_path / "data")
    db   = str(tmp_path / "data/poh.db")
    port = unused_udp_port

    server_task = asyncio.create_task(listen_udp(port, base, db))
    await asyncio.sleep(0.3)  # listener ready

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: asyncio.DatagramProtocol(), remote_addr=("127.0.0.1", port)
    )
    transport.sendto(b"p")
    transport.close()

    await asyncio.sleep(0.3)  # flush
    server_task.cancel()
    with suppress(asyncio.CancelledError):
        await server_task
