# D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\rvh_stable\cli.py
"""
CLI for rvh_stable:

Usage:
  rvh-stable --key 12345 --buckets 10 [--async]
"""
import argparse
import sys

from .stable import jump_hash, async_jump_hash
import asyncio

def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rvh_stable",
        description="Stable (Jump) Hash CLI"
    )
    p.add_argument("--key",      required=True, help="Input key")
    p.add_argument("--buckets",  type=int, required=True, help="Number of buckets")
    p.add_argument(
        "-a", "--async",
        action="store_true",
        dest="use_async",
        help="Use async version",
    )
    return p

def main() -> None:
    args = _build_cli().parse_args()

    if args.use_async:
        # 非同期版：ただ asyncio.run して結果だけを出力
        shard = asyncio.run(async_jump_hash(args.key, args.buckets))
    else:
        # 同期版
        shard = jump_hash(args.key, args.buckets)

    # テストが期待するのは「標準出力に数字のみ」で、stderr は空
    print(shard)

if __name__ == "__main__":
    main()
