# device_manager/device_model.py
from dataclasses import dataclass, asdict
import json
from datetime import datetime

@dataclass
class Device:
    uuid: str   # ここを "user_uuid" から "uuid" に変更      
    device_id: str
    device_name: str
    registered_at: str
    is_active: bool
    login_at: str  # ← 追加！

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            uuid=data.get("uuid", ""),
            device_id=data.get("device_id", ""),
            device_name=data.get("device_name", ""),
            registered_at=data.get("registered_at", datetime.utcnow().isoformat()),
            is_active=data.get("is_active", True),
            login_at=data.get("login_at", datetime.utcnow().isoformat())
        )
