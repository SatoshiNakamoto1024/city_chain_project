# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\cli.py
# poh_batcher/poh_batcher/cli.py
from __future__ import annotations

import asyncio
import sys
from typing import NoReturn

import click
from poh_ack.models import AckRequest

from .batcher import AsyncBatcher
from .storage import storage_from_url
from .types import PackedBatch, AckItem


@click.command()
@click.option(
    "--batch-size", "-n", default=500, show_default=True,
    help="1 バッチあたりの最大 ACK 件数",
)
@click.option(
    "--batch-timeout", "-t", default=1.5, show_default=True, type=float,
    help="バッチ確定までのタイムアウト秒",
)
@click.option(
    "--output-dir", "-o", default="file://./batches", show_default=True,
    help='保存先: "file:///path" or "s3://bucket/prefix"',
)
def main(batch_size: int, batch_timeout: float, output_dir: str) -> NoReturn:
    """
    stdin から1行1ACK JSONを読み、非同期バッチ圧縮→出力するCLI。
    """

    async def _run() -> None:
        storage = storage_from_url(output_dir)
        seq = 0

        async def sink(batch: PackedBatch) -> None:
            nonlocal seq
            ext = ".json.zst" if batch.header.compression == "zstd" else ".json.gz"
            fname = f"batch_{seq:04d}{ext}"
            seq += 1
            await storage.save_bytes(fname, batch.payload)

        batcher = AsyncBatcher(
            max_items=batch_size,
            timeout=batch_timeout,
            sink=sink,
        )
        await batcher.start()
        click.echo(
            f"▶ Batcher start — size={batch_size}, timeout={batch_timeout}s → {output_dir}",
            err=True,
        )

        loop = asyncio.get_running_loop()
        try:
            while True:
                line: str = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    ack_item = AckItem.model_validate_json(line)
                except Exception as e:
                    click.echo(f"⚠ Invalid JSON skipped: {e}", err=True)
                    continue

                # AckItem → AckRequest に変換して enqueue
                req = AckRequest(
                    id=ack_item.id,
                    timestamp=ack_item.timestamp,
                    signature=ack_item.signature,
                    pubkey=ack_item.pubkey,
                )
                await batcher.enqueue(req)

        except KeyboardInterrupt:
            click.echo("⏹ KeyboardInterrupt — flushing...", err=True)
        finally:
            await batcher.stop()
            click.echo("✔ Batcher stopped.", err=True)

    asyncio.run(_run())
    sys.exit(0)


if __name__ == "__main__":
    main()  # pragma: no cover
