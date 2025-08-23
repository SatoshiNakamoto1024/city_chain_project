# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\models.py
from pydantic import BaseModel, Field


class AckRequest(BaseModel):
    """
    ACK 検証リクエストモデル
    """
    id: str = Field(..., description="トランザクション ID")
    timestamp: str = Field(..., description="RFC3339 形式タイムスタンプ (UTC)")
    signature: str = Field(..., description="Base58-encoded Ed25519 signature")
    pubkey: str = Field(..., description="Base58-encoded Ed25519 public key")


class AckResult(BaseModel):
    """
    ACK 検証結果モデル
    """
    id: str = Field(..., description="トランザクション ID")
    valid: bool = Field(..., description="検証結果: True=有効, False=無効")
    error: str | None = Field(None, description="失敗時のエラーメッセージ")
