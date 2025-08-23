# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\app_config.py
# poh_config/app_config.py

"""
poh_config CLI エントリポイント

サブコマンド:
  load   — 設定ファイルを読み込んで JSON で標準出力
  watch  — 設定ファイルを監視し、変更時に JSON で標準出力
"""

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Optional

from .config import ConfigManager


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="poh-config")
    sub = p.add_subparsers(dest="cmd", required=True)

    # load
    ld = sub.add_parser("load", help="load config and print JSON")
    ld.add_argument("path", type=Path, help="path to config file (.toml|.json|.yaml)")

    # watch
    wt = sub.add_parser("watch", help="watch config file and print JSON on change")
    wt.add_argument("path", type=Path, help="path to config file (.toml|.json|.yaml)")
    wt.add_argument(
        "--debounce",
        type=float,
        default=0.1,
        help="debounce interval (seconds) to coalesce rapid changes"
    )

    return p


def _install_signal_handlers(loop: asyncio.AbstractEventLoop):
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(loop)))
        except NotImplementedError:
            # Windows などでは未実装
            pass


async def _shutdown(loop: asyncio.AbstractEventLoop):
    for task in [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]:
        task.cancel()
    await asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True)
    loop.stop()


async def main(argv: Optional[list[str]] = None):
    args = build_parser().parse_args(argv)
    loop = asyncio.get_running_loop()
    _install_signal_handlers(loop)

    cfg_path: Path = args.path
    if not cfg_path.exists():
        print(f"error: file not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    mgr = ConfigManager(cfg_path)

    if args.cmd == "load":
        data = await mgr.load()
        print(json.dumps(data, indent=2))

    elif args.cmd == "watch":
        debounce = args.debounce
        last_call = 0.0

        async def on_change(data: dict):
            nonlocal last_call
            now = loop.time()
            if now - last_call < debounce:
                return
            last_call = now
            print(json.dumps(data, indent=2))

        # 初回ロード＋出力
        init = await mgr.load()
        print(json.dumps(init, indent=2))
        # 以降ファイル監視
        await mgr.watch(on_change)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
