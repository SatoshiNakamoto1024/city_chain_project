# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_integration.py

"""
PoH‑ACK Rust & Python End-to-End Integration Test

This script verifies:
 1. Rust CLI binary (`main_ack`)
 2. Python synchronous API (`verify_ack`)
 3. Python asynchronous API (`verify_ack_async`)
 4. Python CLI synchronous (`poh-ack verify`)
 5. Python CLI asynchronous (`poh-ack verify-async`)

Usage:
    python poh_ack_integration.py
"""

import sys
import os
from pathlib import Path

script_dir = Path(os.path.abspath(__file__)).parent

print("script start", flush=True)
print("cwd =", os.getcwd(), flush=True)
print("__file__ =", __file__, flush=True)
print("exists? ->", (Path(__file__).resolve().parent / "poh_ack_rust").exists(), flush=True)

import asyncio
import json
import shutil
import subprocess
from datetime import datetime, timezone

import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# Python 側のモデル＆検証関数
from poh_ack.models import AckRequest
from poh_ack.verifier import verify_ack, verify_ack_async

# インストール済みの Rust 拡張をインポート

# -------------- build‑artefact name ----------------------------
BIN_NAME = "main_ack.exe" if os.name == "nt" else "main_ack"

# ─ Rust CLI バイナリのパスを自動検出 ────────────────────────────────────────
_root = Path(__file__).parent
rust_rel = _root / "poh_ack_rust" / "target" / "release" / BIN_NAME
rust_dbg = _root / "poh_ack_rust" / "target" / "debug" / BIN_NAME
if rust_rel.exists():
    RUST_CLI = str(rust_rel)
elif rust_dbg.exists():
    RUST_CLI = str(rust_dbg)
else:
    print(" Cannot find main_ack binary. Please run `cargo build [--release]` first.", file=sys.stderr)
    sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────


def make_test_ack(id: str, timestamp: str) -> AckRequest:
    """
    Ed25519 キーペアを生成し、canonical payload を署名して
    AckRequest を返すユーティリティ
    """
    sk = Ed25519PrivateKey.generate()
    vk = sk.public_key()
    payload = f'{{"id":"{id}","timestamp":"{timestamp}"}}'.encode("utf-8")
    sig = sk.sign(payload)
    pk_bytes = vk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return AckRequest(
        id=id,
        timestamp=timestamp,
        signature=base58.b58encode(sig).decode(),
        pubkey=base58.b58encode(pk_bytes).decode(),
    )


def write_req(tmpdir: Path, req: AckRequest) -> Path:
    """
    AckRequest を JSON にシリアライズして一時ファイルに書き出し、
    そのパスを返す
    """
    file_path = tmpdir / f"{req.id}.json"
    file_path.write_text(json.dumps(req.model_dump()), encoding="utf-8")
    return file_path


def test_rust_cli(tmpdir: Path):
    """Rust CLI (`main_ack --input ...`) の同期テスト"""
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack("rust_integration", now)
    path = write_req(tmpdir, req)

    cmd = [RUST_CLI, "--input", str(path), "--ttl", "60"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(" Rust CLI failed:", result.stderr, file=sys.stderr)
        sys.exit(1)
    expected = f"'{req.id}' is valid"
    if expected not in result.stdout:
        print(" Rust CLI unexpected output:", result.stdout, file=sys.stderr)
        sys.exit(1)
    print("✅ Rust CLI passed")


def test_python_sync_api():
    """Python 同期 API (`verify_ack`) のテスト"""
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack("py_sync_integration", now)
    res = verify_ack(req, ttl_seconds=60)
    if not res.valid:
        print(" Python sync API failed:", res.error, file=sys.stderr)
        sys.exit(1)
    print("✅ Python sync API passed")


async def test_python_async_api():
    """Python 非同期 API (`verify_ack_async`) のテスト"""
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack("py_async_integration", now)
    res = await verify_ack_async(req, ttl_seconds=60)
    if not res.valid:
        print(" Python async API failed:", res.error, file=sys.stderr)
        sys.exit(1)
    print("✅ Python async API passed")


def test_python_cli_sync(tmpdir: Path):
    """Python CLI 同期モード (`poh-ack verify`) のテスト"""
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack("py_cli_sync_integration", now)
    path = write_req(tmpdir, req)

    cmd = [
        sys.executable, "-m", "poh_ack.cli", "verify",
        "--input", str(path),
        "--ttl", "60",
        "--json-output",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(" Python CLI sync failed:", result.stderr, file=sys.stderr)
        sys.exit(1)
    out = json.loads(result.stdout)
    if not (out.get("valid") is True and out.get("id") == req.id):
        print(" Python CLI sync unexpected output:", result.stdout, file=sys.stderr)
        sys.exit(1)
    print("✅ Python CLI sync passed")
    # ▼ 失敗時に内容を確認できるよう常に表示しておくと便利
    print("STDOUT→", result.stdout)
    print("STDERR→", result.stderr, file=sys.stderr)


def test_python_cli_async(tmpdir: Path):
    """Python CLI 非同期モード (`poh-ack verify-async`) のテスト"""
    now = datetime.now(timezone.utc).isoformat()
    req = make_test_ack("py_cli_async_integration", now)
    path = write_req(tmpdir, req)

    cmd = [
        sys.executable, "-m", "poh_ack.cli", "verify-async",
        "--input", str(path),
        "--ttl", "60",
        "--json-output",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(" Python CLI async failed:", result.stderr, file=sys.stderr)
        sys.exit(1)
    out = json.loads(result.stdout)
    if not (out.get("valid") is True and out.get("id") == req.id):
        print(" Python CLI async unexpected output:", result.stdout, file=sys.stderr)
        sys.exit(1)
    print("✅ Python CLI async passed")


def main():
    tmpdir = Path("./_integration_tmp")
    if tmpdir.exists():
        shutil.rmtree(tmpdir)
    tmpdir.mkdir()

    # 1) Rust CLI
    test_rust_cli(tmpdir)

    # 2) Python 同期 API
    test_python_sync_api()

    # 3) Python 非同期 API
    asyncio.run(test_python_async_api())

    # 4) Python CLI 同期
    test_python_cli_sync(tmpdir)

    # 5) Python CLI 非同期
    test_python_cli_async(tmpdir)

    print("\n All Rust & Python integration tests passed!")


if __name__ == "__main__":
    main()
