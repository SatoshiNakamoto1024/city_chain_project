# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\app_network.py
"""
poh_network CLI エントリポイント

主要サブコマンド
    add-peer      … ピアを登録
    remove-peer   … ピアを削除
    list-peers    … 登録済みピア一覧表示
    broadcast     … 単発ブロードキャストを実行
    serve-grpc    … gRPC サーバを起動
    serve-http    … HTTP サーバを起動
    listen-udp    … UDP リスナを起動
"""

import argparse
import asyncio
import base64
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from poh_storage.types import Tx
from poh_network.peer_manager import PeerManager
from poh_network.network import NetworkManager
from poh_network.grpc_server import serve as serve_grpc
from poh_network.http_server import run_http_server
from poh_network.udp_listener import listen_udp

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("poh_network.cli")


# --------------------------------------------------------------------------- #
# ヘルパー：Ctrl-C で全サーバを優雅に落とす
# --------------------------------------------------------------------------- #
def _install_signal_handlers(loop: asyncio.AbstractEventLoop):
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(loop)))
        except NotImplementedError:
            # Windows: add_signal_handler が未実装
            pass


async def _shutdown(loop: asyncio.AbstractEventLoop):
    _logger.info("shutdown requested")
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


# --------------------------------------------------------------------------- #
# CLI パーサ
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="poh-network")
    sub = p.add_subparsers(dest="cmd", required=True)

    # peer ops
    sp_add = sub.add_parser("add-peer", help="register peer")
    sp_add.add_argument("--protocol", choices=("grpc", "http", "udp"), required=True)
    sp_add.add_argument("--address", required=True)

    sp_rm = sub.add_parser("remove-peer", help="remove peer")
    sp_rm.add_argument("--protocol", choices=("grpc", "http", "udp"), required=True)
    sp_rm.add_argument("--address", required=True)

    sub.add_parser("list-peers", help="list registered peers")

    # broadcast
    sp_bc = sub.add_parser("broadcast", help="broadcast single Tx")
    sp_bc.add_argument("--tx-json", help='{"tx_id":..,"holder_id":..,"timestamp":..,"payload_b64":..}', required=True)

    # servers
    g = sub.add_parser("serve-grpc", help="start gRPC server")
    g.add_argument("--port", type=int, required=True)
    g.add_argument("--base", required=True)
    g.add_argument("--db", required=True)

    h = sub.add_parser("serve-http", help="start HTTP server")
    h.add_argument("--port", type=int, required=True)
    h.add_argument("--base", required=True)
    h.add_argument("--db", required=True)

    u = sub.add_parser("listen-udp", help="start UDP listener")
    u.add_argument("--port", type=int, required=True)
    u.add_argument("--base", required=True)
    u.add_argument("--db", required=True)

    return p


# --------------------------------------------------------------------------- #
# ペアリング用の非常に簡易なピアデータ永続化（~/.poh_peers.json）
# --------------------------------------------------------------------------- #
_PEER_FILE = Path.home() / ".poh_peers.json"


def _load_peer_file() -> PeerManager:
    pm = PeerManager()
    if _PEER_FILE.exists():
        with _PEER_FILE.open("r", encoding="utf-8") as f:
            d = json.load(f)
        for proto, lst in d.items():
            for addr in lst:
                pm.add_peer(proto, addr)
    return pm


def _save_peer_file(pm: PeerManager) -> None:
    data = {proto: pm.get_peers(proto) for proto in ("grpc", "http", "udp")}
    _PEER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# メイン
# --------------------------------------------------------------------------- #
async def main(argv: Optional[list[str]] = None):
    args = build_parser().parse_args(argv)
    loop = asyncio.get_running_loop()
    _install_signal_handlers(loop)

    # ---------------- peer ops ----------------
    if args.cmd in ("add-peer", "remove-peer", "list-peers"):
        pm = _load_peer_file()

        if args.cmd == "add-peer":
            pm.add_peer(args.protocol, args.address)
            _save_peer_file(pm)
            print("added:", args.protocol, args.address)

        elif args.cmd == "remove-peer":
            pm.remove_peer(args.protocol, args.address)
            _save_peer_file(pm)
            print("removed:", args.protocol, args.address)

        else:  # list-peers
            for proto in ("grpc", "http", "udp"):
                print(proto, ":", pm.get_peers(proto))

        return

    # ---------------- broadcast ----------------
    if args.cmd == "broadcast":
        pm = _load_peer_file()
        nm = NetworkManager(pm)

        data = json.loads(args.tx_json)
        tx = Tx(
            tx_id=data["tx_id"],
            holder_id=data["holder_id"],
            timestamp=data["timestamp"],
            payload=base64.b64decode(data["payload_b64"]),
        )
        ok_grpc, ok_http, ok_udp = await nm.broadcast(tx)
        print("grpc OK:", ok_grpc, "/ http OK:", ok_http, "/ udp OK:", ok_udp)
        return

    # ---------------- servers / listeners ----------------
    if args.cmd == "serve-grpc":
        await serve_grpc(args.port, args.base, args.db)

    elif args.cmd == "serve-http":
        await run_http_server(args.port, args.base, args.db)

    elif args.cmd == "listen-udp":
        await listen_udp(args.port, args.base, args.db)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
