# auth_py/client_cert/make_request_json.py
"""
client_keygen を呼び出して
POST 用 JSON（uuid + 2 公開鍵）を表示する小さなユーティリティ
"""

import sys, os, json, base64
from pathlib import Path

# ❶ プロジェクトルートを import パスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[3]   # city_chain_project/
sys.path.append(str(PROJECT_ROOT))

# ❷ いまのフォルダにある client_keygen をインポート
from login.auth_py.client_cert.client_keygen import generate_client_keys

# ❸ 好きなユーザー ID をここで指定
uuid_val = "user123"

keys = generate_client_keys()
ntru_b64 = base64.b64encode(keys["ntru_public"]).decode()
dil_hex  = keys["dilithium_public"].hex() if isinstance(keys["dilithium_public"], bytes) else keys["dilithium_public"]

req_json = {
    "uuid": uuid_val,
    "ntru_public_b64": ntru_b64,
    "dil_public_hex":  dil_hex
}

print(json.dumps(req_json, indent=2, ensure_ascii=False))
