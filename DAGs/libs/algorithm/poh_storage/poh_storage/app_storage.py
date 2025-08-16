# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\app_storage.py
"""
CLI for poh_storage: init/save/load/delete/list/recover
"""
import argparse
import asyncio
import base64
import json
import logging
import sys
from .storage import StorageManager
from poh_storage.types import Tx

logging.basicConfig(level=logging.INFO)


def parse_args(args=None):
    parser = argparse.ArgumentParser(prog="poh-storage")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub_init = sub.add_parser("init")
    sub_init.add_argument("--base", required=True)
    sub_init.add_argument("--db",   required=True)

    sub_save = sub.add_parser("save")
    sub_save.add_argument("--base", required=True)
    sub_save.add_argument("--db",   required=True)
    sub_save.add_argument("--tx",   required=True,
                           help='Tx JSON: {"tx_id":"...","holder_id":"...","timestamp":0.0,"payload":"base64"}')

    sub_load = sub.add_parser("load")
    sub_load.add_argument("--base", required=True)
    sub_load.add_argument("--db",   required=True)
    sub_load.add_argument("--tx-id", required=True)

    sub_delete = sub.add_parser("delete")
    sub_delete.add_argument("--base", required=True)
    sub_delete.add_argument("--db",   required=True)
    sub_delete.add_argument("--tx-id", required=True)

    sub_list = sub.add_parser("list")
    sub_list.add_argument("--base", required=True)
    sub_list.add_argument("--db",   required=True)

    sub_recov = sub.add_parser("recover")
    sub_recov.add_argument("--base", required=True)
    sub_recov.add_argument("--db",   required=True)

    # args が None なら sys.argv[1:] を使い、リストが渡されたらそれを使う
    return parser.parse_args(args)


async def main(argv=None):
    # 引数パース
    args = parse_args() if argv is None else parse_args(argv)

    # StorageManager 作成
    manager = await StorageManager.create(args.base, args.db)

    # コマンド処理
    if args.cmd == "init":
        print("Initialized storage at", args.base, args.db)

    elif args.cmd == "save":
        j       = json.loads(args.tx)
        payload = base64.b64decode(j["payload"])
        tx      = Tx(tx_id=j["tx_id"], holder_id=j["holder_id"], timestamp=j["timestamp"])
        tx.payload = payload
        await manager.save_tx(tx)
        print(f"Saved tx {tx.tx_id}")

    elif args.cmd == "load":
        tx = await manager.load_tx(args.tx_id)
        print(tx)

    elif args.cmd == "delete":
        await manager.delete_tx(args.tx_id)
        print(f"Deleted tx {args.tx_id}")

    elif args.cmd == "list":
        ids = await manager.list_txs()
        print("No transactions found" if not ids else "Transactions: " + ", ".join(ids))

    elif args.cmd == "recover":
        valid = await manager.recover()
        print(f"Recovery complete: {len(valid)} valid txs")

    else:
        print("Unknown command", args.cmd)

    # --- 後片付け -----------------------------------------------------------------
    # 1) aiosqlite のコネクションを閉じる
    try:
        conn = manager.sqlite_store._conn
        if conn:
            await conn.close()
    except Exception:
        pass

    # 2) デフォルト ThreadPoolExecutor をシャットダウン
    loop = asyncio.get_running_loop()
    await loop.shutdown_default_executor()

if __name__ == "__main__":
    import asyncio
    import sys

    if sys.platform == "win32":
        # Windows では asyncio の EventLoopPolicy を明示設定
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())