# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\schema.py
# poh_request/schema.py
"""Typed Pydantic models for PoH_REQUEST."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import field_serializer
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import SettingsConfigDict


class PoHRequest(BaseModel):
    """
    Outbound PoH_REQUEST transaction.

    * `signature` が `None` の間は未署名。
    * テストの monkey‑patch を許可するため `extra="allow"`。
    """

    type: Literal["poh_request"] = "poh_request"
    token_id: str
    holder_id: str
    amount: int = Field(..., ge=1, description="Positive integer amount")
    nonce: int
    created_at: datetime
    signature: Optional[str] = None  # Base58(Ed25519 signature)

    # ――― モデル設定 ――― #
    model_config = SettingsConfigDict(extra="allow")

    # ――― 生成後バリデーション ――― #
    @model_validator(mode="after")
    def _ensure_aware(cls, v: "PoHRequest"):  # noqa: N805
        """
        `created_at` が naive な場合は UTC 扱いに補正。
        """
        if v.created_at.tzinfo is None:
            v.created_at = v.created_at.replace(tzinfo=timezone.utc)
        return v

    # ---- 追加: datetime を常に ISO‑8601 へ ----
    @field_serializer("created_at", when_used="always")
    def _ser_dt(self, v: datetime) -> str:          # noqa: D401, N802
        """Serialize datetime as UTC ISO‑8601 w/ seconds precision."""
        return v.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


class PoHResponse(BaseModel):
    """
    Inbound response from PoH RPC.
    """

    txid: str
    status: Literal["accepted", "queued", "rejected"]
    received_at: datetime
    reason: Optional[str] = None  # error detail if rejected
