# user_manager/profile/profile_edit.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def edit_profile_data(user_uuid: str, new_data: dict) -> dict:
    """
    プロフィールデータを直接ローカル保存ファイルで書き換える。
    実際にはDynamoDBと整合性を取るかもしれないが、サンプル実装。
    """
    folder_path = os.path.join("user_manager", "profile", "profile_data")
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, f"profile_{user_uuid}.json")

    old_data = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            old_data = json.load(f)

    old_data.update(new_data)
    old_data["last_edit"] = datetime.utcnow().isoformat() + "Z"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(old_data, f, ensure_ascii=False, indent=2)
    return old_data
