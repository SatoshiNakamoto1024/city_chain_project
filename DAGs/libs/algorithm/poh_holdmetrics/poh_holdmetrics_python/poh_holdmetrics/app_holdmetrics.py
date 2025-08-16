# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\app_holdmetrics.py
# -*- coding: utf-8 -*-
"""
CLI ランチャー

* `grpc` サブコマンド  … gRPC サーバのみ起動
* `http` サブコマンド  … HTTP (FastAPI) サーバのみ起動
* `all`  サブコマンド  … 両方並列で起動
"""

from __future__ import annotations

import asyncio
import logging

import click
import uvicorn

from .api.grpc_server import serve_grpc
from .api.http_server import app as http_app
from .config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), "INFO"))


@click.group()
def cli() -> None:
    """PoH-Hold-Metrics service controller"""


# ------------------------------------------------------------------
# サブコマンド群
# ------------------------------------------------------------------
@cli.command()
def grpc() -> None:  # noqa: D401
    """Run only gRPC server"""
    # ここは“そのまま”呼ぶ。asyncio.run は serve_grpc 内でやっている
    serve_grpc(settings.grpc_address)


@cli.command()
def http() -> None:  # noqa: D401
    """Run only HTTP server"""
    uvicorn.run(
        http_app,
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )


@cli.command()
def all() -> None:  # noqa: D401
    """Run gRPC + HTTP concurrently"""
    async def _serve_all() -> None:
        grpc_task = asyncio.create_task(serve_grpc(settings.grpc_address))

        uv_cfg = uvicorn.Config(
            http_app,
            host=settings.http_host,
            port=settings.http_port,
            log_level=settings.log_level.lower(),
            lifespan="off",  # gRPC と同居時にシャットダウン干渉を防ぐ
        )
        http_server = uvicorn.Server(uv_cfg)
        http_task = asyncio.create_task(http_server.serve())

        await asyncio.gather(grpc_task, http_task)

    asyncio.run(_serve_all())


if __name__ == "__main__":
    cli()
