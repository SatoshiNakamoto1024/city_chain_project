import jsonschema
from .models import FreshTx, PoHRequestTx
from .errors import ValidationError

# JSON Schema定義（必要なだけ追加）
FRESH_TX_SCHEMA = {
    "type": "object",
    "properties": {
        "tx_id": {"type": "string"},
        "type": {"const": "FRESH_TX"},
        "sender": {"type": "string"},
        "receiver": {"type": "string"},
        "amount": {"type": "number", "exclusiveMinimum": 0},
        "payload": {"type": "object"},
        "timestamp": {"type": "string", "format": "date-time"}
    },
    "required": ["tx_id", "type", "sender", "receiver", "amount", "payload", "timestamp"]
}

def validate_raw(raw: dict) -> None:
    """JSON schema レベルのバリデーション"""
    tx_type = raw.get("type")
    if tx_type == "FRESH_TX":
        schema = FRESH_TX_SCHEMA
    elif tx_type == "POH_REQUEST":
        # schema = POH_REQUEST_SCHEMA
        raise NotImplementedError
    else:
        raise ValidationError(f"未知のTx type: {tx_type}")

    try:
        jsonschema.validate(instance=raw, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"JSON Schema違反: {e.message}")

def parse_and_validate(raw: dict):
    """
    Pydantic を使った詳細バリデーションと型キャスト
    """
    validate_raw(raw)
    tx_type = raw["type"]
    try:
        if tx_type == "FRESH_TX":
            return FreshTx(**raw)
        elif tx_type == "POH_REQUEST":
            return PoHRequestTx(**raw)
        else:
            raise ValidationError(f"サポート外TxType: {tx_type}")
    except Exception as e:
        # Pydantic のエラーもここで拾ってラップ
        raise ValidationError(f"Pydantic違反: {e}")
