# login/auth_py/client_cert_handler.py
"""
client_cert_handler.py
──────────────────────
PEM 形式のクライアント証明書を

  • SHA-256 Finger-Print へ変換
  • ローカル保存／ロード

だけを行うユーティリティ。  
DynamoDB など DB 周りは上位レイヤが呼び出す。
"""
from __future__ import annotations
import base64, hashlib, os
from pathlib import Path
from datetime import datetime, timezone

# ──────────────────────────────────────────────
# 保存ディレクトリ
# ──────────────────────────────────────────────
STORE_DIR = Path(
    os.getenv("CLIENT_CERT_STORE", r"D:\city_chain_project\login\login_data\user_client_cert_pem")
)
STORE_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# 内部ヘルパ
# ──────────────────────────────────────────────
def _pem_to_der(pem: str) -> bytes:
    """----- 行を削って base64 デコード → DER"""
    b64 = "".join(l for l in pem.splitlines() if "-----" not in l)
    return base64.b64decode(b64)


def pem_fingerprint(pem: str) -> str:
    """PEM → SHA-256 Finger-Print（hex40 ではなく 64 桁 hex）"""
    der = _pem_to_der(pem)
    return hashlib.sha256(der).hexdigest()


# ──────────────────────────────────────────────
# 公開 API
# ──────────────────────────────────────────────
def save_cert(uuid_val: str, pem_str: str) -> Path:
    """uuid.pem として保存し、保存先 Path を返す"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = STORE_DIR / f"{uuid_val}_{ts}.pem"
    path.write_text(pem_str, encoding="utf-8")
    return path


def load_cert(uuid_val: str) -> str:
    """最新の PEM をロードして文字列で返す（見つからなければ IOError）"""
    cands = sorted(STORE_DIR.glob(f"{uuid_val}_*.pem"), reverse=True)
    if not cands:
        raise FileNotFoundError(f"no pem for {uuid_val}")
    return cands[0].read_text(encoding="utf-8")
