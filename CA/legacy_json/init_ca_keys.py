# CA/init_ca_keys.py

import os
import json
import sys

# dilithium-py のパスを追加
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from app_dilithium import create_keypair

# 保存先パス
KEY_DIR = "CA/keys"
os.makedirs(KEY_DIR, exist_ok=True)

# 🔥 Dilithiumの鍵生成
public_key, private_key = create_keypair()

# 🔥 リスト型なら bytes型に直してからhex変換
if isinstance(public_key, list):
    public_key = bytes(public_key)
if isinstance(private_key, list):
    private_key = bytes(private_key)

# 保存する内容
ca_key_data = {
    "private_key": private_key.hex(),
    "public_key": public_key.hex(),
    "issuer": "ExampleCA",
    "created_at": "2025-04-24"
}

# 保存ファイル
output_path = os.path.join(KEY_DIR, "ca_private.json")
with open(output_path, "w") as f:
    json.dump(ca_key_data, f, indent=4)

print(f"✅ CA鍵を保存しました: {output_path}")
