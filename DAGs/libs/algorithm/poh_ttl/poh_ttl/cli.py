# D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\poh_ttl\cli.py
import argparse
import asyncio
import logging
import sys

from poh_storage.storage import StorageManager
from .manager import TTLManager

logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(prog="poh-ttl")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan", help="Run one-time TTL scan")
    p.add_argument("--base", required=True, help="data directory")
    p.add_argument("--db", required=True, help="SQLite DB path")
    p.add_argument("--ttl", type=int, required=True, help="TTL seconds")

    p2 = sub.add_parser("run", help="Run continuous TTL GC")
    p2.add_argument("--base", required=True)
    p2.add_argument("--db", required=True)
    p2.add_argument("--ttl", type=int, required=True)
    p2.add_argument("--interval", type=int, required=True, help="Interval seconds")

    return parser.parse_args()


async def main():
    args = parse_args()
    sm = await StorageManager.create(args.base, args.db)
    ttl = TTLManager(sm, args.ttl)

    if args.cmd == "scan":
        expired = await ttl.scan_once()
        print("Expired:", expired)

    elif args.cmd == "run":
        ttl.run(args.interval)
        # 永遠に動かす
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

    await sm.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
