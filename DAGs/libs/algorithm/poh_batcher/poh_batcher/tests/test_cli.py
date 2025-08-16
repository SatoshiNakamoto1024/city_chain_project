# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\tests\test_cli.py
"""
test_cli.py
===========

`poh_batcher.cli` のエンドツーエンドテスト。

* click.testing.CliRunner で subprocess 無し実行
* 出力ファイルが 1 個以上作成されることを確認
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from click.testing import CliRunner

from poh_batcher.cli import main as cli_main

# -----------------------------------------------------------------------------


def _sample_ack(i: int) -> str:
    """最小限のダミー ACK JSON"""
    return json.dumps(
        {
            "id": f"tx{i}",
            "timestamp": "2099-01-01T00:00:00Z",
            "signature": "1" * 88,
            "pubkey": "1" * 44,
        }
    )


def test_cli_batch(tmp_path: Path, monkeypatch) -> None:
    # --- 準備: 入力データを JSON Lines で生成 -------------------------------
    lines = "\n".join(_sample_ack(i) for i in range(5)) + "\n"

    # バッチ保存用ディレクトリ
    out_dir = tmp_path / "batches"

    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "--batch-size",
            "2",
            "--batch-timeout",
            "0.1",
            "--output-dir",
            f"file://{out_dir}",
        ],
        input=lines,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output

    # --- 検証: ファイルが生成されている -------------------------------
    batch_files = list(out_dir.rglob("*.json*"))
    assert batch_files, "no batch files created"

    # 各ファイルは JSON 配列として parse できる
    for path in batch_files:
        raw = (path.read_bytes()).rstrip(b"\n\r")
        # gzip / zstd 対応
        if path.suffix == ".gz":
            import gzip

            raw = gzip.decompress(raw)
        elif path.suffix == ".zst":
            import zstandard as zstd

            raw = zstd.ZstdDecompressor().decompress(raw)  # type: ignore[attr-defined]
        data = json.loads(raw)
        assert isinstance(data, list)
        for item in data:
            assert "id" in item
