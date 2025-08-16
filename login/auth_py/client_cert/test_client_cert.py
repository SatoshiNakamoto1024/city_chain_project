# test_client_cert.py

import sys
import uuid
from pathlib import Path
import base64, requests

# プロジェクト構成に合わせてパス追加
PROJECT_ROOT    = Path(__file__).resolve().parents[3]
AUTH_PY_DIR     = PROJECT_ROOT / "login" / "auth_py"
CLIENT_CERT_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(CLIENT_CERT_DIR), str(AUTH_PY_DIR)]

from client_keygen import generate_client_keys
from dilithium_verify import (
    extract_ntru_pub_from_spki,
    extract_dilithium_pub_from_spki,
    verify_pem,
)

CLIENT_API = "http://localhost:6001"

def json_headers():
    return {"Content-Type": "application/json"}

def step1():
    keys = generate_client_keys()
    req = {
        "uuid": f"test-user-{uuid.uuid4().hex[:8]}",
        "ntru_public_b64": base64.b64encode(keys['ntru_public']).decode(),
        "dil_public_hex":  keys['dilithium_public'].hex()
    }
    print("[1] 鍵ペア生成 → JSON 化 OK")
    return req, keys['ntru_public'], keys['dilithium_public']

def step2(req):
    r = requests.post(f"{CLIENT_API}/client_cert", json=req,
                      headers=json_headers(), timeout=10)
    assert r.status_code == 200, r.text
    print("[2] /client_cert POST → 200 OK")
    return r.json()["pem"]

def step3(pem_str, orig_ntru, orig_dil):
    pem = pem_str.encode()

    #  テスト用に一旦ファイルとして保存
    debug_path = Path("temp_debug.pem")
    debug_path.write_bytes(pem)
    print(f"PEM を {debug_path} に保存しました")

    #  SPKI.subjectPublicKey から NTRU 鍵
    extracted_ntru = extract_ntru_pub_from_spki(pem)
    assert extracted_ntru == orig_ntru, "SPKI から取り出した NTRU 鍵が一致しません"

    # SPKI.algorithm.parameters から Dilithium 鍵
    extracted_dil = extract_dilithium_pub_from_spki(pem)
    assert extracted_dil == orig_dil, "SPKI.parameters から取り出した Dilithium 鍵が一致しません"

    # 署名検証
    assert verify_pem(pem), "署名検証に失敗しました"
    print("[3] NTRU/Dilithium 鍵取り出し＆署名検証 → OK")

def step4(uuid):
    r = requests.get(f"{CLIENT_API}/download_cert_pem",
                     params={"uuid": uuid}, timeout=10)
    assert r.status_code == 200, r.text
    print("[4] ダウンロード OK")

def step5(uuid):
    r = requests.post(f"{CLIENT_API}/revoke_cert",
                      json={"uuid": uuid}, headers=json_headers(), timeout=10)
    assert r.status_code == 200 and r.json().get('revoked') is True
    print("[5] 失効 OK")

def test_client_cert_flow():
    """
    end-to-end テスト:
    step1～step5 を順番に実行
    """
    req, orig_ntru, orig_dil = step1()
    pem = step2(req)
    step3(pem, orig_ntru, orig_dil)
    step4(req['uuid'])
    step5(req['uuid'])
