# D:\city_chain_project\network\sending_DAGs\python_sending\common\app_common.py
"""
Unified CLI / Dev-launcher for the `common` package.

$ python -m common.app_common --help
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from concurrent import futures
from pathlib import Path
from types import ModuleType
from typing import Optional

import grpc

# ──────────────────────────────────────────────
# 「common パッケージ」を動的 import（editable-install 無しでも動くように）
# ──────────────────────────────────────────────
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]  # プロジェクトルートを推定
sys.path.append(str(ROOT))

import common as C      # ここでエラーが出なくなる

logger = logging.getLogger("common.cli")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
)

# ──────────────────────────────────────────────
# 1) 動的バッチ間隔
# ──────────────────────────────────────────────
def cmd_batch_interval(args: argparse.Namespace) -> None:
    interval = C.config.get_dynamic_batch_interval(args.pending)
    print(f"pending={args.pending}  interval={interval:.2f}s")


# ──────────────────────────────────────────────
# 2) MongoDB へダミー Tx 保存
# ──────────────────────────────────────────────
def cmd_save_tx(args: argparse.Namespace) -> None:
    doc = {
        "tx_id": f"tx_{int(time.time())}",
        "amount": random.randint(1, 100),
        "status": "completed",
    }
    oid = C.db_handler.save_completed_tx_to_mongo(doc, args.collection)
    print(f"inserted ObjectId = {oid}")


# ──────────────────────────────────────────────
# 3) ローカル分散ストレージへフラグ保存 / 復元
# ──────────────────────────────────────────────
def cmd_store_frag(args: argparse.Namespace) -> None:
    ok = C.distributed_storage_system.store_transaction_frag(
        node_id=args.node,
        tx_id=args.tx_id,
        shard_id=args.shard,
        data={"sample": True, "ts": time.time()},
    )
    print("store =", ok)


def cmd_restore_frag(args: argparse.Namespace) -> None:
    data = C.distributed_storage_system.restore_transaction_frag(
        node_id=args.node,
        tx_id=args.tx_id,
        shard_id=args.shard,
    )
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ──────────────────────────────────────────────
# 4) 簡易 Storage gRPC サーバ起動（開発用）
# ──────────────────────────────────────────────
def _load_storage_proto() -> Optional[ModuleType]:
    """
    storage_pb2 / storage_pb2_grpc を動的 import.
    プロトバッファコードが未生成なら None を返す。
    """
    try:
        from common.proto import storage_pb2, storage_pb2_grpc  # type: ignore
        return storage_pb2, storage_pb2_grpc
    except ModuleNotFoundError:
        logger.error(
            "storage_pb2.py が見つかりません。先に\n"
            "  $ python -m grpc_tools.protoc -I common/proto "
            "--python_out=common/proto --grpc_python_out=common/proto "
            "common/proto/storage.proto\nで生成して下さい。"
        )
        return None


def cmd_storage_server(args: argparse.Namespace) -> None:
    loaded = _load_storage_proto()
    if loaded is None:
        sys.exit(1)
    storage_pb2, storage_pb2_grpc = loaded  # noqa: N806

    class DevStorageServicer(storage_pb2_grpc.StorageServiceServicer):  # type: ignore
        def StoreFragment(self, request, context):  # noqa: N802
            folder = Path("./_tmp_storage")
            folder.mkdir(exist_ok=True)
            fname = folder / f"{request.tx_id}_{request.shard_id}.bin"
            fname.write_bytes(request.data)
            logger.info("stored %s (%d bytes)", fname, len(request.data))
            return storage_pb2.StoreResponse(success=True, message="ok")

    opts = [
        ("grpc.keepalive_time_ms", 10_000),
        ("grpc.keepalive_timeout_ms", 5_000),
    ]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4), options=opts)
    storage_pb2_grpc.add_StorageServiceServicer_to_server(DevStorageServicer(), server)
    port = server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    print(f"[StorageServer] listening on {port} … Ctrl-C で停止")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nStop.")


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="common.app_common",
        description="Toolkit launcher / dev-server for the `common` package",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # 1) batch
    p = sub.add_parser("batch", help="動的バッチ間隔を確認")
    p.add_argument("--pending", type=int, default=0, help="pending Tx 数")
    p.set_defaults(func=cmd_batch_interval)

    # 2) save
    p = sub.add_parser("save", help="MongoDB にダミー Tx を保存")
    p.add_argument("--collection", default="completed_transactions")
    p.set_defaults(func=cmd_save_tx)

    # 3-a) store
    p = sub.add_parser("store", help="ローカル分散ストレージへ保存")
    p.add_argument("--node", required=True)
    p.add_argument("--tx-id", default="demo")
    p.add_argument("--shard", default="0")
    p.set_defaults(func=cmd_store_frag)

    # 3-b) restore
    p = sub.add_parser("restore", help="ローカル分散ストレージから復元")
    p.add_argument("--node", required=True)
    p.add_argument("--tx-id", default="demo")
    p.add_argument("--shard", default="0")
    p.set_defaults(func=cmd_restore_frag)

    # 4) storage-server
    p = sub.add_parser("storage-server", help="簡易 Storage gRPC サーバを起動")
    p.add_argument("--port", type=int, default=50070)
    p.set_defaults(func=cmd_storage_server)

    return ap


def _main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    _main()
