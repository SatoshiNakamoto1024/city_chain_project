# login/wallet/wallet_model.py
from dataclasses import dataclass, asdict, field
from decimal import Decimal
from datetime import datetime
import json

@dataclass
class Wallet:
    wallet_address: str
    user_uuid: str
    balance: Decimal = field(default_factory=lambda: Decimal("0"))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        """API 返却用（float に戻す）"""
        d = asdict(self)
        d["balance"] = float(d["balance"])
        return d

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            wallet_address=d["wallet_address"],
            user_uuid=d["user_uuid"],
            balance=Decimal(str(d.get("balance", 0))),
            created_at=d.get("created_at", datetime.utcnow().isoformat()),
            updated_at=d.get("updated_at", datetime.utcnow().isoformat())
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)
