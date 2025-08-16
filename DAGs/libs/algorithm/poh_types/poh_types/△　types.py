# D:\city_chain_project\DAGs\libs\algorithm\poh_types\poh_types\types.py
from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from typing import ClassVar
from .exceptions import PoHTypesError


@dataclass
class PoHTx:
    """
    PoH トランザクションの基底データ構造。
    tx_id, holder_id, timestamp は必須フィールド。
    """
    tx_id: str
    holder_id: str
    timestamp: float

    # クラスレベルの許容ドリフト幅 (秒)
    ALLOW_DRIFT: ClassVar[float] = 1.0

    def __post_init__(self):
        if not self.tx_id:
            raise PoHTypesError("tx_id must be non-empty")
        if not self.holder_id:
            raise PoHTypesError("holder_id must be non-empty")
        if not isinstance(self.timestamp, (int, float)):
            raise PoHTypesError("timestamp must be a number")

    def to_json(self) -> str:
        """同期的に JSON 文字列へシリアライズ"""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, text: str) -> PoHTx:
        """同期的に JSON 文字列からインスタンス化"""
        data = json.loads(text)
        return cls(**data)

    async def to_json_async(self) -> str:
        """非同期的に JSON 文字列へシリアライズ"""
        # ここでは実際非同期処理しないが、IO バウンド時などに拡張可能
        return self.to_json()

    async def from_json_async(cls, text: str) -> PoHTx:
        """非同期的に JSON 文字列からインスタンス化"""
        return cls.from_json(text)

    async def validate_timestamp(self, allow_drift: float | None = None) -> None:
        """
        非同期でタイムスタンプの検証を行う。
        allow_drift 秒以上古い場合に例外を投げる。
        """
        import time
        now = time.time()
        drift = allow_drift if allow_drift is not None else self.ALLOW_DRIFT
        if abs(now - self.timestamp) > drift:
            raise PoHTypesError(f"timestamp drift too large: {abs(now - self.timestamp):.3f}s")


@dataclass
class PoHReq(PoHTx):
    """
    保存依頼 PoH_REQUEST。
    追加情報があればここに定義 (現状は基底と同じ)。
    """
    pass


@dataclass
class PoHAck(PoHTx):
    """
    保存証明 PoH_ACK。
    storage_hash, sig_alg, signature を追加。
    """
    storage_hash: str
    sig_alg: str
    signature: str

    def __post_init__(self):
        super().__post_init__()
        if not self.storage_hash:
            raise PoHTypesError("storage_hash must be non-empty")
        if not self.sig_alg:
            raise PoHTypesError("sig_alg must be non-empty")
        if not self.signature:
            raise PoHTypesError("signature must be non-empty")
