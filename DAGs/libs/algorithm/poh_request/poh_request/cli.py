# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\cli.py
"""Console entry‑points for poh‑request CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from nacl import signing

from .builder import PoHRequestBuilder
from .schema import PoHResponse
from .sender import send_sync
from .utils import b58decode

app = typer.Typer(help="PoH_REQUEST Tx builder & sender CLI")


def _load_signing_key(path: Path) -> signing.SigningKey:
    return signing.SigningKey(path.read_bytes())


# ---------------------------------------------------------------------- #
# build
# ---------------------------------------------------------------------- #
@app.command()
def build(
    token_id: str = typer.Option(...),
    holder_id: str = typer.Option(...),
    amount: int = typer.Option(..., min=1),
    key: Path = typer.Option(..., exists=True, readable=True),
    nonce: Optional[int] = typer.Option(None),
    out: Optional[Path] = typer.Option(None, help="Write payload to file"),
) -> None:
    sk = _load_signing_key(key)
    payload = (
        PoHRequestBuilder(
            sk,
            token_id=token_id,
            holder_id=holder_id,
            amount=amount,
            nonce=nonce,
        )
        .sign()
        .encode()
    )
    if out:
        out.write_text(payload)
        typer.echo(f"Wrote payload to {out}")
    else:
        typer.echo(payload)


# ---------------------------------------------------------------------- #
# send
# ---------------------------------------------------------------------- #
@app.command()
def send(
    payload: Optional[Path] = typer.Argument(
        None, help="File containing Base58 payload (or stdin)"
    ),
) -> None:
    raw = payload.read_text().strip() if payload else sys.stdin.read().strip()
    resp: PoHResponse = send_sync(raw)
    typer.echo(resp.model_dump_json(indent=2))


# ---------------------------------------------------------------------- #
# decode
# ---------------------------------------------------------------------- #
@app.command()
def decode(payload: str = typer.Argument(...)) -> None:
    typer.echo(json.dumps(json.loads(b58decode(payload)), indent=2))


if __name__ == "__main__":
    app()
