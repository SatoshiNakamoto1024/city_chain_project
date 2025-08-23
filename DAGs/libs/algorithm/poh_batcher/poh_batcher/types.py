# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\types.py
# poh_batcher/types.py

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class AckItem(BaseModel):
    """
    CLI が JSON Lines から読み込む ACK アイテム。
    Test CLI が使うモデルです。
    """
    id: str
    timestamp: str
    signature: str
    pubkey: str


class BatchHeader(BaseModel):
    """
    圧縮バッチのヘッダ情報
    """
    count: int
    compression: Literal["gzip", "zstd"]


class PackedBatch(BaseModel):
    """
    圧縮バッチ本体
    """
    header: BatchHeader
    payload: bytes

    class Config:
        # raw バイト列を Pydantic が受け取れるように
        allow_mutation = False
        json_encoders = {bytes: lambda b: b}
