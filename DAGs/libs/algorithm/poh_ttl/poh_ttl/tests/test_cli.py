# D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\poh_ttl\tests\test_cli.py
import subprocess
import sys
import asyncio
from pathlib import Path
import pytest

from poh_storage.storage import StorageManager
from poh_storage.types   import Tx

# -u: unbuffered 出力（バッファ詰まり防止）
SCRIPT = [sys.executable, "-u", "-m", "poh_ttl.cli"]

def run(cmd):
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=True,
        timeout=30,
    )

def test_scan(tmp_path):
    base = tmp_path / "data"
    db   = tmp_path / "data" / "poh.db"

    # 1) ストレージ初期化
    sm = asyncio.run(StorageManager.create(str(base), str(db)))
    # 2) 古いタイムスタンプのTxを保存
    tx = Tx(tx_id="1", holder_id="h", timestamp=0.0, payload=b"p")
    asyncio.run(sm.save_tx(tx))
    asyncio.run(sm.close())

    # 3) scanコマンド実行
    result = run(SCRIPT + ["scan", "--base", str(base), "--db", str(db), "--ttl", "1"])
    assert "Expired: ['1']" in result.stdout

    # 4) 2回目は何も消えない
    result = run(SCRIPT + ["scan", "--base", str(base), "--db", str(db), "--ttl", "1"])
    assert "Expired: []" in result.stdout
