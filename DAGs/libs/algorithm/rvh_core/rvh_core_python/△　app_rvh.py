# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_python\app_rvh.py

"""
CLI サンプル:

    python -m rvh_python.app_rvh \
        -n "node1,node2,node3" \
        -k tx-XYZ \
        -c 2
"""
from __future__ import annotations

import argparse
from .rvh_builder import rendezvous_hash, RVHError


def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app_rvh",
        description="Rendezvous-Hash (HRW) CLI",
    )
    p.add_argument(
        "-n", "--nodes",
        required=True,
        help="カンマ区切りのノード一覧 (例: node1,node2,node3)",
    )
    p.add_argument(
        "-k", "--key",
        required=True,
        help="オブジェクトキー (例: tx-XYZ)",
    )
    p.add_argument(
        "-c", "--count",
        required=True,
        type=int,
        metavar="K",
        help="選出ノード数 k",
    )
    return p


def main() -> None:  # pragma: no cover
    args = _build_cli().parse_args()
    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    try:
        selected = rendezvous_hash(nodes, args.key, args.count)
        print(f"key='{args.key}' → selected: {selected}")
    except RVHError as e:
        print(f"[ERROR] {e}", flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
