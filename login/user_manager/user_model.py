# File: user_manager/user_model.py

import sys
import os
# user_manager の１つ上をパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dataclasses import dataclass, asdict
from datetime import datetime
import json

@dataclass
class User:
    uuid: str
    name: str = ""
    birth_date: str = ""
    address: str = ""
    mynumber: str = ""
    email: str = ""
    phone: str = ""
    password_hash: str = ""
    salt: str = ""
    public_key: str = ""
    dilithium_public_key: str = ""
    client_cert_fingerprint: str = ""
    created_at: str = ""
    session_id: str = "REGISTRATION"

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
            dilithium_public_key=data.get("dilithium_public_key", ""),
            client_cert_fingerprint=data.get("client_cert_fingerprint", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            session_id=data.get("session_id", "REGISTRATION")
        )
