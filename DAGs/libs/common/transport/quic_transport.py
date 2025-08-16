# city_chain_project\network\DAGs\common\transport\quic_transport.py
"""
QUIC/HTTP3 トランスポート (aioquic ベース)

※ 実運用時は aioquic のバージョンや HTTP/3 API に合わせて拡張してください。
"""
from __future__ import annotations
import asyncio
from aioquic.asyncio import serve, connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN, H3Connection
from typing import Optional


class QUICServer:
    """
    QUIC + HTTP/3 サーバー基盤

    Parameters
    ----------
    host : str
    port : int
    handler_factory : Callable[[], asyncio.Protocol]
        aioquic 用プロトコルファクトリ
    cert : Optional[str]
        サーバー証明書ファイル (.pem)
    key : Optional[str]
        サーバー秘密鍵ファイル (.pem)
    """

    def __init__(
        self,
        host: str,
        port: int,
        handler_factory: Callable[[], asyncio.Protocol],
        cert: str | None = None,
        key: str | None = None,
    ):
        config = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
        if cert and key:
            config.load_cert_chain(cert, key)
        self._host = host
        self._port = port
        self._config = config
        self._factory = handler_factory
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        """サーバーを起動"""
        self._server = await serve(
            host=self._host,
            port=self._port,
            configuration=self._config,
            create_protocol=self._factory,
        )

    async def close(self) -> None:
        """サーバー停止"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()


class QUICClient:
    """
    QUIC + HTTP/3 クライアント基盤

    Parameters
    ----------
    host : str
    port : int
    cafile : Optional[str]
        CA ルート証明書 (.pem) for server verification
    """

    def __init__(self, host: str, port: int, cafile: str | None = None):
        config = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
        if cafile:
            config.load_verify_locations(cafile)
        self._host = host
        self._port = port
        self._config = config

    async def request(self, data: bytes) -> bytes:
        """
        単純な QUIC データ送信/受信
        （HTTP/3 レイヤーを自前で実装する場合はここを拡張）
        """
        async with connect(self._host, self._port, configuration=self._config) as protocol:
            stream_id = protocol._quic.get_next_available_stream_id()
            protocol._quic.send_stream_data(stream_id, data, end_stream=True)
            await protocol.wait_connected()

            # 応答をひたすら受け取る
            response = bytearray()
            while True:
                event = await protocol._quic.wait_for_event()
                from aioquic.h3.events import DataReceived
                if isinstance(event, DataReceived) and event.stream_id == stream_id:
                    response.extend(event.data)
                    if event.stream_ended:
                        break
            return bytes(response)
