# user_manager/user_model.py
from datetime import datetime
from dataclasses import dataclass, asdict
import json

@dataclass
class User:
    uuid: str
    name: str
    birth_date: str
    address: str
    mynumber: str
    email: str
    phone: str
    password_hash: str
    salt: str
    public_key: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            uuid=data.get("uuid", ""),
            name=data.get("name", ""),
            birth_date=data.get("birth_date", ""),
            address=data.get("address", ""),
            mynumber=data.get("mynumber", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            password_hash=data.get("password_hash", ""),
            salt=data.get("salt", ""),
            public_key=data.get("public_key", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat())
        )
