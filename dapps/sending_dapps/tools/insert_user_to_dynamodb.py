# File: sending_dapps/tools/insert_user_to_dynamodb.py
#!/usr/bin/env python
"""
insert_user_to_dynamodb.py

  _fixtures/ にある PEM 由来の鍵情報を
  DynamoDB UsersTable (PK=uuid, SK=session_id) へ 1 行登録するだけのツール
"""

import boto3, json, os, sys
from pathlib import Path

# ── 1. 出力フォルダを “sending_dapps/_fixtures” に固定 ──
SENDING_DAPPS_DIR = Path(__file__).resolve().parents[1]   # …/sending_dapps
FIX = SENDING_DAPPS_DIR / "_fixtures"

# 存在チェック
if not FIX.exists():
    sys.exit(f"[ERROR] _fixtures フォルダが見つかりません: {FIX}")

# ── 2. 生成済みファイルを読む ─────────────────────────────
try:
    NTRU_SK_B64 = (FIX / "ntru_sk.b64").read_text().strip()
    DILI_PUB_B64 = (FIX / "dilithium_pub.b64").read_text().strip()
except FileNotFoundError as e:
    sys.exit(f"[ERROR] 必要ファイルが不足しています: {e}")

# ── 3. UUID はコマンドライン引数で渡す ───────────────────
#    例)  python insert_user_to_dynamodb.py fixture_user_ab12cd
if len(sys.argv) != 2:
    sys.exit("Usage: python insert_user_to_dynamodb.py <USER_UUID>")

USER_UUID = sys.argv[1].strip()
if not USER_UUID:
    sys.exit("USER_UUID が空です")

# ── 4. DynamoDB 登録用 Item を組立 ──────────────────────
item = {
    "uuid": USER_UUID,
    "session_id": "USER_PROFILE",
    "username":   "Fixture_User",
    "region":     "Asia",
    "ntru_secret_key_b64": NTRU_SK_B64,
    "dilithium_public_key": DILI_PUB_B64
}

AWS_REGION  = os.getenv("AWS_REGION", "us-east-1")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")

# ── 5. PutItem ───────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table     = dynamodb.Table(USERS_TABLE)
table.put_item(Item=item)

print("✓ UsersTable に登録完了")
print(json.dumps(item, indent=2, ensure_ascii=False))
