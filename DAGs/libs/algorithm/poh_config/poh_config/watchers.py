# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\watchers.py
# poh_config/watchers.py

"""
ファイル変更をポーリングで検知し、自動リロード＆コールバックを行うユーティリティ。

- プラットフォームを問わず動作（inotify 未対応の WSL / network-mounted FS 等でも OK）
- デフォルトで debounce: 0.1 秒
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict

from .config import ConfigManager

async def watch_file(
    path: Path,
    on_change: Callable[[Dict[str, Any]], Any],
    *,
    debounce: float = 0.1
) -> None:
    """
    path をポーリング監視し、mtime が変化したら on_change(new_data) を呼び出します。

    Args:
        path: 監視対象のファイルパス
        on_change: 新しい設定 dict を引数に取るコールバック関数
        debounce: ポーリング間隔 & 連続検知をまとめる時間 (秒)
    """
    # ConfigManager を初期化
    mgr = ConfigManager(path)

    # --- 初回ロード & コールバック ---
    data = await mgr.load()
    await on_change(data)

    # 初回の mtime を記憶
    try:
        last_mtime = path.stat().st_mtime
    except FileNotFoundError:
        last_mtime = 0.0

    # --- ポーリングループ ---
    while True:
        await asyncio.sleep(debounce)
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            # ファイル削除→再作成の可能性も考慮
            continue

        if mtime != last_mtime:
            last_mtime = mtime
            # 設定再ロード & コールバック
            new_data = await mgr.load()
            await on_change(new_data)
