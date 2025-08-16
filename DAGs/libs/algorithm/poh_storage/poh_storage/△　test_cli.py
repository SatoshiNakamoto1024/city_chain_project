# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tests\test_cli.py
import pytest
import subprocess
import sys
import base64
import json
from pathlib import Path

# -u: unbuffered 出力（バッファ詰まり防止）
SCRIPT = [sys.executable, "-u", "-m", "poh_storage.app_storage"]

def run(cmd):
    # init/save/delete コマンドは出力を捨てる
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def test_cli(tmp_path):
    base = tmp_path / "data"
    db   = tmp_path / "data" / "poh.db"

    # init
    run(SCRIPT + ["init", "--base", str(base), "--db", str(db)])

    # save
    tx = {
        "tx_id":     "1",
        "holder_id": "h",
        "timestamp": 0.0,
        "payload":   base64.b64encode(b"payload").decode()
    }
    run(SCRIPT + [
        "save",
        "--base", str(base),
        "--db",   str(db),
        "--tx",   json.dumps(tx)
    ])

    # list → stdout をキャプチャして検証
    result = subprocess.run(
        SCRIPT + ["list", "--base", str(base), "--db", str(db)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
    )
    assert b"1" in result.stdout

    # load → stdout をキャプチャして検証
    result = subprocess.run(
        SCRIPT + [
            "load",
            "--base", str(base),
            "--db",   str(db),
            "--tx-id", "1"
        ],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
    )
    assert b"tx_id='1'" in result.stdout

    # delete
    run(SCRIPT + [
        "delete",
        "--base", str(base),
        "--db",   str(db),
        "--tx-id", "1"
    ])

    # recover → stdout をキャプチャして検証
    result = subprocess.run(
        SCRIPT + ["recover", "--base", str(base), "--db", str(db)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True
    )
    assert b"Recovery complete:" in result.stdout
