# D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\rvh_stable\app_stable.py
# !/usr/bin/env python3
"""
CLI for rvh_stable: Jump Consistent Hash の同期／非同期呼び分け
"""

import sys
import argparse
import asyncio
import logging

from .stable import jump_hash, async_jump_hash


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app_stable",
        description="Jump Consistent Hash CLI (Google Jump Hash)",
    )
    p.add_argument(
        "--key",
        required=True,
        help="Key string to hash",
    )
    p.add_argument(
        "--buckets",
        required=True,
        type=int,
        help="Number of buckets (must be >=1)",
    )
    p.add_argument(
        "-a", "--async",
        action="store_true",
        dest="use_async",
        help="Use async version",
    )
    p.add_argument(
        "--level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level for debug",
    )
    return p


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.level:
        logging.basicConfig(level=getattr(logging, args.level.upper()))

    try:
        if args.use_async:
            # 非同期版
            result = asyncio.run(async_jump_hash(args.key, args.buckets))
        else:
            # 同期版
            result = jump_hash(args.key, args.buckets)
        # テストはここで stdout にだけ数字を出力し、stderr は出してはいけない
        print(result)
    except Exception as e:
        # 何か例外が起きたら stderr にメッセージ、exit code=1
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
