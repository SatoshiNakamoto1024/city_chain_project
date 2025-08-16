# user_manager/lifeform/lifeform_check.py

import json
import os

def validate_lifeform_dimensions(lifeform_data: dict) -> bool:
    """
    生命体データの次元が30以下であることなどを簡易チェック
    """
    dims = lifeform_data.get("dimensions", {})
    if len(dims) > 30:
        return False
    return True

def load_lifeform_from_local(lifeform_id: str) -> dict:
    """
    ローカルに保存された lifeform_data から読み込む
    """
    filepath = os.path.join("user_manager", "lifeform", "lifeform_data", f"{lifeform_id}.json")
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
