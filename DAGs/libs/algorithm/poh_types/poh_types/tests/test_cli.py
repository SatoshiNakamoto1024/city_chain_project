# D:\city_chain_project\DAGs\libs\algorithm\poh_types\poh_types\tests\test_cli.py
import subprocess
import sys
import json
import time
import pytest

PYTHON = sys.executable
MODULE = "poh_types.app_types"

def run(cmd_args):
    """`python -m poh_types.app_types <cmd_args>` を実行し、(code, stdout, stderr) を返す。"""
    proc = subprocess.run(
        [PYTHON, "-m", MODULE] + cmd_args,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr

def test_generate_req_basic():
    code, out, err = run(["req", "--tx-id", "tx1", "--holder-id", "nodeA"])
    assert code == 0
    data = json.loads(out)
    assert data["tx_id"] == "tx1"
    assert data["holder_id"] == "nodeA"
    assert isinstance(data["timestamp"], (int, float))

def test_generate_ack_basic():
    code, out, err = run([
        "ack",
        "--tx-id", "tx2",
        "--holder-id", "nodeB",
        "--storage-hash", "deadbeef",
        "--sig-alg", "dilithium3",
        "--signature", "Zm9vYmFy"
    ])
    assert code == 0
    data = json.loads(out)
    assert data["storage_hash"] == "deadbeef"
    assert data["sig_alg"] == "dilithium3"
    assert data["signature"] == "Zm9vYmFy"

def test_validate_ok():
    now = time.time()
    code, out, err = run([
        "validate",
        "--tx-id", "tx3",
        "--holder-id", "nodeC",
        "--timestamp", str(now),
        "--allow-drift", "5"
    ])
    assert code == 0
    assert out.strip() == "OK"

def test_validate_fail():
    old = time.time() - 10.0
    code, out, err = run([
        "validate",
        "--tx-id", "tx4",
        "--holder-id", "nodeD",
        "--timestamp", str(old),
        "--allow-drift", "1"
    ])
    assert code != 0
    assert "[ERROR]" in err
