from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Device:
    uuid: str            # ユーザーUUID
    device_id: str       # デバイスID
    device_name: str     # デバイス名
    registered_at: str   # 登録日時 (ISO8601)
    is_active: bool      # 有効フラグ
    login_at: str        # 最後にログインした日時 (ISO8601)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            uuid          = data.get("uuid", ""),
            device_id     = data.get("device_id", ""),
            device_name   = data.get("device_name", ""),
            registered_at = data.get("registered_at", datetime.utcnow().isoformat()),
            is_active     = data.get("is_active", True),
            login_at      = data.get("login_at", datetime.utcnow().isoformat())
        )
