# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\cli.py
"""
軽量 CLI:

$ rvh-filter -n "a,b,bad-x,validator-1" --deny-regex "bad.*" --deny "validator-1"
"""
from __future__ import annotations

import argparse
import sys

from .filter_core import filter_nodes, FilterError


def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rvh-filter",
        description="Node exclusion (blacklist / regex / predicate) CLI",
    )
    p.add_argument(
        "-n", "--nodes",
        required=True,
        help="Comma-separated node IDs",
    )
    p.add_argument(
        "--deny",
        action="append",
        default=[],
        metavar="NODE_ID",
        help="Blacklist node ID (can repeat)",
    )
    p.add_argument(
        "--deny-regex",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Blacklist regex pattern (can repeat, Python syntax)",
    )
    return p


def main() -> None:  # pragma: no cover
    args = _build_cli().parse_args()
    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    try:
        out = filter_nodes(nodes, blacklist=set(args.deny), regex_deny=args.deny_regex)
    except FilterError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        raise SystemExit(1) from e
    print(",".join(out))


if __name__ == "__main__":
    main()
