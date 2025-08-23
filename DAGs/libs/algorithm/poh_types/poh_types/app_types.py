# D:\city_chain_project\DAGs\libs\algorithm\poh_types\poh_types\app_types.py
# !/usr/bin/env python3
"""
CLI for poh_types: PoHTx (base), PoHReq and PoHAck の生成およびタイムスタンプ検証。
"""

import argparse
import sys
import time
import asyncio

from .types import PoHTx, PoHReq, PoHAck
from .exceptions import PoHTypesError


def _cmd_generate_req(args):
    ts = args.timestamp if args.timestamp is not None else time.time()
    try:
        req = PoHReq(tx_id=args.tx_id, holder_id=args.holder_id, timestamp=ts)
        print(req.to_json())
    except PoHTypesError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_generate_ack(args):
    ts = args.timestamp if args.timestamp is not None else time.time()
    try:
        ack = PoHAck(
            tx_id=args.tx_id,
            holder_id=args.holder_id,
            timestamp=ts,
            storage_hash=args.storage_hash,
            sig_alg=args.sig_alg,
            signature=args.signature,
        )
        print(ack.to_json())
    except PoHTypesError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


async def _cmd_validate(args):
    ts = args.timestamp if args.timestamp is not None else time.time()
    try:
        tx = PoHTx(tx_id=args.tx_id, holder_id=args.holder_id, timestamp=ts)
        await tx.validate_timestamp(allow_drift=args.allow_drift)
        print("OK")
    except PoHTypesError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="app_types",
        description="Generate/validate PoHTx, PoHReq and PoHAck JSON",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # PoHReq 生成
    gen_req = sub.add_parser("req", help="Generate PoHReq JSON")
    gen_req.add_argument("--tx-id", required=True, help="Original Tx ID")
    gen_req.add_argument("--holder-id", required=True, help="Holder node ID")
    gen_req.add_argument("--timestamp", type=float, help="UNIX timestamp (seconds)")
    gen_req.set_defaults(func=_cmd_generate_req, async_cmd=False)

    # PoHAck 生成
    gen_ack = sub.add_parser("ack", help="Generate PoHAck JSON")
    gen_ack.add_argument("--tx-id", required=True, help="Original Tx ID")
    gen_ack.add_argument("--holder-id", required=True, help="Holder node ID")
    gen_ack.add_argument("--storage-hash", required=True, help="SHA256 of stored bytes")
    gen_ack.add_argument("--sig-alg", required=True, help="Signature algorithm")
    gen_ack.add_argument("--signature", required=True, help="Base64 signature")
    gen_ack.add_argument("--timestamp", type=float, help="UNIX timestamp (seconds)")
    gen_ack.set_defaults(func=_cmd_generate_ack, async_cmd=False)

    # PoHTx タイムスタンプ検証
    validate = sub.add_parser("validate", help="Validate PoHTx timestamp drift")
    validate.add_argument("--tx-id", required=True, help="Original Tx ID")
    validate.add_argument("--holder-id", required=True, help="Holder node ID")
    validate.add_argument("--timestamp", type=float, required=True, help="Tx timestamp")
    validate.add_argument(
        "--allow-drift",
        type=float,
        default=None,
        help="許容ドリフト秒 (省略時は types.PoHTx.ALLOW_DRIFT を使用)",
    )
    validate.set_defaults(func=_cmd_validate, async_cmd=True)

    args = parser.parse_args()
    if getattr(args, "async_cmd", False):
        asyncio.run(args.func(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
