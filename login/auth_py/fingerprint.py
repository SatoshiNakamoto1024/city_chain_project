# login/auth_py/fingerprint.py
"""
fingerprint.py
─────────────────────────────────────────────
fingerprint（証明書フィンガープリント）関連のユーティリティを
“ここだけ見ればわかる”形でまとめ直しました。
"""

from __future__ import annotations
import base64
import hashlib
import json
import re
from typing import Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend


_HEX_RE = re.compile(r"[0-9a-fA-F]")            # 16 進数 1 文字


# ───────────────────────── public helpers ────────────────────────────
def normalize_fp(fp: str | bytes) -> str:
    """
    * 大文字小文字／コロン／スペースを吸収して
      「aa11bb22...」という lower‑hex のみに統一
    * bytes の場合は hex() → 同様に整形
    """
    if isinstance(fp, bytes):
        fp = fp.hex()

    return "".join(ch.lower() for ch in fp if _HEX_RE.match(ch))


def calc_fp_from_pem(pem: str | bytes) -> str:
    """
    PEM 文字列/bytes → SHA‑256 → lower‑hex（コロン等を除去）を返す
    （Base64(JSON) を誤って渡されたら中の "pem" を抽出して続行）
    """
    if isinstance(pem, bytes):
        pem_bytes = pem
    else:
        if pem.lstrip().startswith("{"):          # ← Base64(JSON) 想定
            pem = json.loads(pem)["pem"]
        pem_bytes = pem.encode()

    sha256_hex = hashlib.sha256(pem_bytes).hexdigest()
    return normalize_fp(sha256_hex)
