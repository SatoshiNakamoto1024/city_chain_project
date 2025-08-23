# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\cli.py
# poh_ack/cli.py
# ---------------------------------------------------------------------------------
# Command‑line utilities for PoH‑ACK
#   * verify          … 同期検証
#   * verify-async    … 非同期検証
# ---------------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Final

import click

from .models import AckRequest
from .verifier import verify_ack, verify_ack_async

# ────────────────────────────────────────────────────────────────────────────
# Common helpers
# ────────────────────────────────────────────────────────────────────────────
_JSON_SEPS: Final[tuple[str, str]] = (",", ":")


def _load_request(path: str | Path) -> AckRequest:
    """Read a JSON file and parse into `AckRequest` (pydantic)."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return AckRequest.model_validate(data)


def _echo_result(res, json_output: bool) -> None:
    """Print verification result either as compact JSON or a human string."""
    if json_output:
        click.echo(json.dumps(res.model_dump(), separators=_JSON_SEPS))
    else:
        status = "VALID" if res.valid else "INVALID"
        msg = f" id={res.id}"
        if res.error:
            msg += f" error='{res.error}'"
        click.echo(f"{status}:{msg}")
        if not res.valid:
            # 非 JSON モードでは exit code = 1 で失敗を示す
            sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────
# Click entry‑point
# ────────────────────────────────────────────────────────────────────────────
@click.group(help="PoH‑ACK verifier utilities")
def cli() -> None:
    """Root command — does nothing."""


# --------------------------------------------------------------------------
# verify  (同期)
# --------------------------------------------------------------------------
@cli.command("verify")
@click.option("--input", "-i",
              type=click.Path(exists=True, dir_okay=False, readable=True),
              required=True,
              help="Path to ACK JSON file")
@click.option("--ttl", "-t",
              type=int,
              default=300,
              show_default=True,
              help="TTL seconds")
@click.option("--json-output",
              is_flag=True,
              help="Emit result as single‑line JSON")
def verify_cmd(input: str, ttl: int, json_output: bool) -> None:
    """Synchronously verify one ACK JSON file."""
    req = _load_request(input)
    res = verify_ack(req, ttl)
    _echo_result(res, json_output)


# --------------------------------------------------------------------------
# verify‑async  (非同期)
# --------------------------------------------------------------------------
@cli.command("verify-async")
@click.option("--input", "-i",
              type=click.Path(exists=True, dir_okay=False, readable=True),
              required=True,
              help="Path to ACK JSON file")
@click.option("--ttl", "-t",
              type=int,
              default=300,
              show_default=True,
              help="TTL seconds")
@click.option("--json-output",
              is_flag=True,
              help="Emit result as single‑line JSON")
def verify_async_cmd(input: str, ttl: int, json_output: bool) -> None:
    """Asynchronously verify one ACK JSON file."""
    async def _run() -> None:
        req = _load_request(input)
        res = await verify_ack_async(req, ttl)
        _echo_result(res, json_output)

    asyncio.run(_run())


# --------------------------------------------------------------------------
# `python -m poh_ack.cli …` で起動された場合
# --------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    cli()  # pylint: disable=no-value-for-parameter
