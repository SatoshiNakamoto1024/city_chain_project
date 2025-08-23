# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_integration.py
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# PoH‑ACK  Rust & Python  end‑to‑end integration test
#   1) Rust CLI           (main_ack)
#   2) Python sync  API   (verify_ack)
#   3) Python async API   (verify_ack_async)
#   4) Python CLI  sync   (poh_ack.cli verify)
#   5) Python CLI  async  (poh_ack.cli verify-async)
# ---------------------------------------------------------------------------

import sys
import os
import platform
import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# ───────────────────────────────────  import 汚染を防ぐ
SCRIPT_DIR = Path(__file__).resolve().parent
for p in ("", str(SCRIPT_DIR)):
    if p in sys.path:
        sys.path.remove(p)

# ───────────────────────────────────  依存ライブラリ
import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from poh_ack.models import AckRequest
from poh_ack.verifier import verify_ack, verify_ack_async
import poh_ack_rust as _rust   # noqa: F401  (import side‑effect)

# ───────────────────────────────────  Rust CLI binary 検出
BIN = "main_ack.exe" if platform.system() == "Windows" else "main_ack"
_root = SCRIPT_DIR / "poh_ack_rust" / "target"
RUST_CLI = None
for prof in ("release", "debug"):
    p = _root / prof / BIN
    if p.exists():
        RUST_CLI = str(p); break
if RUST_CLI is None:
    sys.exit("❌  main_ack binary not found – run `cargo build --release`")


# ───────────────────────────────────  util
def _canonical(i: str, ts: str) -> bytes:
    return f'{{"id":"{i}","timestamp":"{ts}"}}'.encode()


def make_ack(aid: str, ts: str) -> AckRequest:
    sk = Ed25519PrivateKey.generate(); vk = sk.public_key()
    sig = sk.sign(_canonical(aid, ts))
    return AckRequest(
        id=aid, timestamp=ts,
        signature=base58.b58encode(sig).decode(),
        pubkey=base58.b58encode(
            vk.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)).decode())


def write_json(tmp: Path, ack: AckRequest) -> Path:
    p = tmp / f"{ack.id}.json"
    p.write_text(json.dumps(ack.model_dump()), encoding="utf‑8"); return p


# clean PYTHONPATH をサブプロセスに渡す
BASE_ENV = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}


# ───────────────────────────────────  tests
def _last_json_line(stdout: str) -> dict:
    """
    標準出力の最後の非空行を JSON として読み込む。
    Rust モジュールの print 汚染対策。
    """
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line:
            return json.loads(line)
    raise ValueError("no JSON line in stdout")


def test_rust_cli(tmp: Path) -> None:
    ack = make_ack("rust", datetime.now(timezone.utc).isoformat())
    res = subprocess.run(
        [RUST_CLI, "--input", str(write_json(tmp, ack)), "--ttl", "60"],
        text=True, capture_output=True)
    assert res.returncode == 0, res.stderr
    assert f"'{ack.id}' is valid" in res.stdout
    print("✅ Rust CLI passed")


def test_py_sync() -> None:
    assert verify_ack(make_ack("py_sync", datetime.now(timezone.utc).isoformat()), 60).valid
    print("✅ Python sync API passed")


async def test_py_async() -> None:
    assert (await verify_ack_async(
        make_ack("py_async", datetime.now(timezone.utc).isoformat()), 60)).valid
    print("✅ Python async API passed")


def _run_cli(cmd: list[str]) -> dict:
    res = subprocess.run(cmd, text=True, capture_output=True,
                         env=BASE_ENV, cwd=str(SCRIPT_DIR))
    assert res.returncode == 0, res.stderr
    return _last_json_line(res.stdout)


def test_cli_sync(tmp: Path) -> None:
    ack = make_ack("cli_sync", datetime.now(timezone.utc).isoformat())
    out = _run_cli([sys.executable, "-m", "poh_ack.cli", "verify",
                    "--input", str(write_json(tmp, ack)), "--ttl", "60", "--json-output"])
    assert out["valid"] and out["id"] == ack.id
    print("✅ Python CLI sync passed")


def test_cli_async(tmp: Path) -> None:
    ack = make_ack("cli_async", datetime.now(timezone.utc).isoformat())
    out = _run_cli([sys.executable, "-m", "poh_ack.cli", "verify-async",
                    "--input", str(write_json(tmp, ack)), "--ttl", "60", "--json-output"])
    assert out["valid"] and out["id"] == ack.id
    print("✅ Python CLI async passed")


# ───────────────────────────────────  entry‑point
def main() -> None:
    tmp = Path("_integration_tmp"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    test_rust_cli(tmp)
    test_py_sync()
    asyncio.run(test_py_async())
    test_cli_sync(tmp)
    test_cli_async(tmp)
    print("\n🎉 All Rust & Python integration tests passed!")


if __name__ == "__main__":
    main()
