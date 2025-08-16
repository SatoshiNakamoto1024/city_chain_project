# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\tests\test_cli.py
import json
from pathlib import Path

import pytest
from nacl import signing
from typer.testing import CliRunner

from poh_request.cli import app
from poh_request.schema import PoHResponse

runner = CliRunner()


def _write_key(tmp: Path) -> Path:
    sk = signing.SigningKey.generate()
    p = tmp / "key.bin"
    p.write_bytes(sk.encode())
    return p


def test_cli_build_and_decode(tmp_path):
    key_file = _write_key(tmp_path)

    # build
    res = runner.invoke(
        app,
        [
            "build",
            "--token-id",
            "TK",
            "--holder-id",
            "H",
            "--amount",
            "5",
            "--key",
            str(key_file),
        ],
    )
    assert res.exit_code == 0
    payload = res.stdout.strip()

    # decode
    res2 = runner.invoke(app, ["decode", payload])
    decoded = json.loads(res2.stdout)
    assert decoded["holder_id"] == "H"


def test_cli_send(monkeypatch, tmp_path):
    sample = "payload"
    f = tmp_path / "p.txt"
    f.write_text(sample)

    dummy = PoHResponse(
        txid="XYZ", status="accepted", received_at="2025-01-01T00:00:00Z"
    )
    monkeypatch.setattr("poh_request.cli.send_sync", lambda _: dummy)

    res = runner.invoke(app, ["send", str(f)])
    assert '"status": "accepted"' in res.stdout


def test_cli_send_stdin(monkeypatch):
    dummy = PoHResponse(
        txid="ABC", status="queued", received_at="2025-01-01T00:00:00Z"
    )
    monkeypatch.setattr("poh_request.cli.send_sync", lambda _: dummy)
    res = runner.invoke(app, ["send"], input="payload")
    assert '"txid": "ABC"' in res.stdout
