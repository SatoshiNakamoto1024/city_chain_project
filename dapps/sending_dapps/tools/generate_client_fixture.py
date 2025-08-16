# File: sending_dapps/tools/generate_client_fixture.py
#!/usr/bin/env python
"""
１回回すだけで _fixtures/ に
  client.pem               … 署名済みクライアント証明書
  ntru_sk.b64              … NTRU   秘密鍵 (Base64)
  dilithium_pub.b64        … Dilithium 公開鍵 (Base64)
  dilithium_sk.b64         … Dilithium 秘密鍵 (Base64)
を作り、ユーザー UUID を表示する。
"""

import base64, uuid, json, os, sys
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from login.auth_py.client_cert.client_keygen import generate_client_keys
from CA.ca_issue_client_cert_asn1              import issue_client_cert

# ── 1. PQC キーペア生成 ────────────────────────────
keys   = generate_client_keys()        # dict -> bytes
ntru_p = keys["ntru_public"]
ntru_s = keys["ntru_private"]
dili_p = keys["dilithium_public"]
dili_s = keys["dilithium_private"]

# ── 2. クライアント PEM を発行（ローカル CA に直接呼び出し） ──
USER_UUID = "fixture_user_" + uuid.uuid4().hex[:8]
pem_bytes = issue_client_cert(ntru_p, dili_p, USER_UUID)   # bytes(PEM)

# ── 3. _fixtures ディレクトリへ保存 ──────────────────
FIX = Path("dapps/sending_dapps/_fixtures")
FIX.mkdir(parents=True, exist_ok=True)

def _w(name: str, data: bytes | str):
    p = FIX / name
    p.write_bytes(data if isinstance(data, bytes) else data.encode())
    return p

_w("client.pem", pem_bytes)
_w("ntru_sk.b64",       base64.b64encode(ntru_s))
_w("dilithium_pub.b64", base64.b64encode(dili_p))
_w("dilithium_sk.b64",  base64.b64encode(dili_s))

print("✓ _fixtures 生成完了")
print(json.dumps({
    "user_uuid": USER_UUID,
    "pem_path": str(FIX/"client.pem")
}, indent=2, ensure_ascii=False))
