# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\app_metrics.py
# poh_metrics/app_metrics.py

"""
poh_metrics CLI エントリポイント。

Usage:
  # メトリクスサーバ起動
  poh-metrics serve --host 0.0.0.0 --port 8000

  # テスト的にデータを収集
  poh-metrics collect --poh-success 5 --poh-failure 1 --verify-success 3 --gc-minor 2 --active-peers 7
"""

import argparse
import asyncio
import sys

from .exporter import start_http_server
from .collector import (
    increment_poh,
    observe_issue,
    observe_verify,
    record_gc,
    set_active_peers,
)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="poh-metrics")
    sub = p.add_subparsers(dest="cmd", required=True)

    # serve
    sv = sub.add_parser("serve", help="start metrics HTTP server")
    sv.add_argument("--host", default="0.0.0.0", help="bind address")
    sv.add_argument("--port", type=int, default=8000, help="port number")

    # collect
    cl = sub.add_parser("collect", help="simulate metrics collection")
    cl.add_argument("--poh-success",   type=int, default=0, help="increment success counter")
    cl.add_argument("--poh-failure",   type=int, default=0, help="increment failure counter")
    cl.add_argument("--poh-timeout",   type=int, default=0, help="increment timeout counter")
    cl.add_argument("--verify-success",type=int, default=0, help="increment verify success")
    cl.add_argument("--verify-failure",type=int, default=0, help="increment verify failure")
    cl.add_argument("--gc-minor",      type=int, default=0, help="record minor GC")
    cl.add_argument("--gc-major",      type=int, default=0, help="record major GC")
    cl.add_argument("--active-peers",  type=int, default=None, help="set active peer count")

    return p

async def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.cmd == "serve":
        await start_http_server(args.host, args.port)

    elif args.cmd == "collect":
        for _ in range(args.poh_success):
            await increment_poh("success")
        for _ in range(args.poh_failure):
            await increment_poh("failure")
        for _ in range(args.poh_timeout):
            await increment_poh("timeout")

        for _ in range(args.verify_success):
            await observe_verify("success", latency=0.0)
        for _ in range(args.verify_failure):
            await observe_verify("failure", latency=0.0)

        if args.gc_minor:
            await record_gc("minor", args.gc_minor)
        if args.gc_major:
            await record_gc("major", args.gc_major)

        if args.active_peers is not None:
            await set_active_peers(args.active_peers)

        print("Metrics collection simulated.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
