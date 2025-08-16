# D:\city_chain_project\network\sending_DAGs\python_sending\common\app_common.py
"""
Unified CLI / Dev-launcher for the `common` package.

$ python -m common.app_common --help
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from concurrent import futures
from pathlib import Path
from types import ModuleType
from typing import Optional

import grpc

# プロジェクトルートを動的に追加（editable-install 無しでも動く）
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import common as C  # noqa: E402  pylint: disable=wrong-import-position

logger = logging.getLogger("common.cli")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

# ════════════════════════════════════════════════════════════
# 1) batch-interval
# ════════════════════════════════════════════════════════════
def cmd_batch_interval(args: argparse.Namespace) -> None:
    interval = C.config.get_dynamic_batch_interval(args.pending)
    print(f"pending={args.pending}  interval={interval:.2f}s")


# ════════════════════════════════════════════════════════════
# 2) MongoDB dummy save
# ════════════════════════════════════════════════════════════
def cmd_save_tx(args: argparse.Namespace) -> None:
    doc = {
        "tx_id": f"tx_{int(time.time())}",
        "amount": random.randint(1, 100),
        "status": "completed",
        "ts": time.time(),
    }
    oid = C.db_handler.save_completed_tx_to_mongo(doc, args.collection)
    print(f"inserted ObjectId = {oid}")


# ════════════════════════════════════════════════════════════
# 3) distributed storage (local json)
# ════════════════════════════════════════════════════════════
def cmd_store_frag(args: argparse.Namespace) -> None:
    ok = C.distributed_storage_system.store_transaction_frag(
        node_id=args.node, tx_id=args.tx_id, shard_id=args.shard, data={"ts": time.time()}
    )
    print("store =", ok)


def cmd_restore_frag(args: argparse.Namespace) -> None:
    data = C.distributed_storage_system.restore_transaction_frag(
        node_id=args.node, tx_id=args.tx_id, shard_id=args.shard
    )
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ════════════════════════════════════════════════════════════
# 4) rebalance (light-node relocation)
# ════════════════════════════════════════════════════════════
def cmd_rebalance(_: argparse.Namespace) -> None:
    moved = C.rebalancer.rebalance_once()
    print(json.dumps(moved, indent=2, ensure_ascii=False))


# ════════════════════════════════════════════════════════════
# 5) reward distribute
# ════════════════════════════════════════════════════════════
def cmd_reward(_: argparse.Namespace) -> None:
    C.reward_system.distribute_once()
    print("✔ reward distribute completed")


# ════════════════════════════════════════════════════════════
# 6) Minimal Storage gRPC dev-server
# ════════════════════════════════════════════════════════════
def _load_storage_proto() -> Optional[tuple[ModuleType, ModuleType]]:
    try:
        from common.proto import storage_pb2, storage_pb2_grpc  # type: ignore
        return storage_pb2, storage_pb2_grpc
    except ModuleNotFoundError:
        logger.error(
            "storage_pb2.py が見つかりません。先に:\n"
            "  python -m grpc_tools.protoc -I common/proto "
            "--python_out=common/proto --grpc_python_out=common/proto "
            "common/proto/storage.proto\nを実行して下さい。"
        )
        return None


def cmd_storage_server(args: argparse.Namespace) -> None:
    loaded = _load_storage_proto()
    if loaded is None:
        sys.exit(1)
    storage_pb2, storage_pb2_grpc = loaded  # noqa: N806

    class DevStorageServicer(storage_pb2_grpc.StorageServiceServicer):  # type: ignore
        def StoreFragment(self, request, context):  # noqa: N802
            folder = Path("./_tmp_storage"); folder.mkdir(exist_ok=True)
            fname = folder / f"{request.tx_id}_{request.shard_id}.bin"
            fname.write_bytes(request.data)
            logger.info("stored %s (%dB)", fname, len(request.data))
            return storage_pb2.StoreResponse(success=True, message="ok")

    opts = [("grpc.keepalive_time_ms", 10_000), ("grpc.keepalive_timeout_ms", 5_000)]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4), options=opts)
    storage_pb2_grpc.add_StorageServiceServicer_to_server(DevStorageServicer(), server)
    port = server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    print(f"[StorageServer] listen on {port} … Ctrl-C to stop")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nStop.")


# ════════════════════════════════════════════════════════════
# CLI parser
# ════════════════════════════════════════════════════════════
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="common.app_common", description="Toolkit launcher")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("batch", help="動的バッチ間隔を確認")
    p.add_argument("--pending", type=int, default=0)
    p.set_defaults(func=cmd_batch_interval)

    p = sub.add_parser("save", help="MongoDB にダミー Tx を保存")
    p.add_argument("--collection", default="completed_transactions")
    p.set_defaults(func=cmd_save_tx)

    p = sub.add_parser("store", help="ローカル分散ストレージへ保存")
    p.add_argument("--node", required=True)
    p.add_argument("--tx-id", default="demo")
    p.add_argument("--shard", default="0")
    p.set_defaults(func=cmd_store_frag)

    p = sub.add_parser("restore", help="ローカル分散ストレージから復元")
    p.add_argument("--node", required=True)
    p.add_argument("--tx-id", default="demo")
    p.add_argument("--shard", default="0")
    p.set_defaults(func=cmd_restore_frag)

    p = sub.add_parser("rebalance", help="オフラインノード再配布 (ライトノード)")
    p.set_defaults(func=cmd_rebalance)

    p = sub.add_parser("reward-distribute", help="報酬トークンを 1 回分配")
    p.set_defaults(func=cmd_reward)

    p = sub.add_parser("storage-server", help="簡易 Storage gRPC サーバを起動")
    p.add_argument("--port", type=int, default=50070)
    p.set_defaults(func=cmd_storage_server)

    return ap


def _main() -> None:  # pragma: no cover
    args = _build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    _main()
