# login/auth_py/client_cert/client_cert_manager.py

import sys, base64
from pathlib import Path

# CAモジュールを直接呼び出す
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CA_DIR = PROJECT_ROOT / "CA"
sys.path.insert(0, str(CA_DIR))
from ca_issue_client_cert_asn1 import issue_client_cert as ca_issue

# ストアディレクトリ
STORE_DIR = Path.home() / ".myapp_certs"
STORE_DIR.mkdir(exist_ok=True)

def request_cert(user_uuid: str, ntru_pub: bytes, dil_pub: bytes) -> Path:
    """
    CA から直接 PEM を受け取り、そのままファイルに保存。
    """
    print(" request_cert() called")
    print(" 呼び出し元 issue_client_cert =", ca_issue.__module__, ca_issue.__name__)
    
    pem_bytes: bytes = ca_issue(ntru_pub, dil_pub, user_uuid)
    
    out_path = STORE_DIR / f"{user_uuid}.pem"
    out_path.write_bytes(pem_bytes)
    print(" PEM 書き込み完了:", out_path)
    return out_path

def load_cert(user_uuid: str) -> bytes:
    """
    ストアから保存済み証明書をバイト列で読み込む。
    """
    return (STORE_DIR / f"{user_uuid}.pem").read_bytes()
