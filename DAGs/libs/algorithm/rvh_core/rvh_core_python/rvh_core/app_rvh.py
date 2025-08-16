# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\app_rvh.py
"""
CLI:

python -m rvh_core.app_rvh \
    --nodes node1,node2,node3 \
    --name obj-XYZ             # ← --key のエイリアス
    --count 2                  # k
    --level debug              # ← 受け取るだけで無視
    --async                    # await 版を使うなら
"""
from __future__ import annotations

import argparse
import asyncio
from .rvh_builder import rendezvous_hash, arendezvous_hash, RVHError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Rendezvous-Hash (HRW) CLI")
    p.add_argument("-n", "--nodes", required=True,
                   help="comma-separated node list")
    # --- key / name をどちらでも取れるように ----------------------
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("-k", "--key", help="object key / id")
    group.add_argument("--name", dest="key_alias",
                       help="alias for --key (for compatibility)")
    # ---------------------------------------------------------------
    p.add_argument("-c", "--count", required=True, type=int, metavar="K",
                   help="number of nodes to return (k)")
    p.add_argument("--async", dest="as_async",
                   action="store_true", help="use async API")
    # level は受け取るだけ（捨てる）
    p.add_argument("--level", default=None, help=argparse.SUPPRESS)
    return p


def main() -> None:  # pragma: no cover
    args = _build_parser().parse_args()

    # key は --key / --name どちらでも OK
    key = args.key if args.key is not None else args.key_alias
    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]

    try:
        if args.as_async:
            sel = asyncio.run(arendezvous_hash(nodes, key, args.count))
        else:
            sel = rendezvous_hash(nodes, key, args.count)
        print(sel)
    except RVHError as e:
        print(f"[ERROR] {e}", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
