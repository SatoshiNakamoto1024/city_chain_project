# File: Algorithm/core/crypto.py
"""
Algorithm.core.crypto
=====================

Production-grade wrapper for *NTRU-HRSS-701* KEM.

* ``wrap_key_ntru(pub_key, key)  -> capsule``  (encapsulate)
* ``unwrap_key_ntru(priv_key, capsule) -> key``  (decapsulate)

優先順位
----------

1. **ntrust_native_py**  (社内／OSS PyO3 ビルド)
2. **pqcrypto.kem.ntruhrss701**  (PyPI)
3. どちらも無ければ ImportError

Both back-ends expose a *KEM* interface:

* **encapsulate(pk) → (ct, ss)**   – 共有鍵 *ss* とカプセル *ct*
* **decapsulate(ct, sk) → ss**

Implementation notes
--------------------

* RFC 9180 (HPKE) とは無関係です。NTRU 専用の KEM。
* 戻り値の「カプセル」はバイト列 (ct)。  
  これを Key Vault に保存し、復号側では `unwrap_key_ntru()` に渡す。
"""

from __future__ import annotations

import importlib
import logging
from typing import Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# back-end detection helpers
# ---------------------------------------------------------------------------


def _load_ntrust_native() -> Tuple:
    try:
        ntru = importlib.import_module("ntrust_native_py")  # type: ignore
        logger.info("Algorithm.core.crypto: using ntrust_native_py back-end")

        def _encapsulate(pub_key: bytes) -> Tuple[bytes, bytes]:
            ct, ss = ntru.encrypt(pub_key)
            return ct, ss

        def _decapsulate(ct: bytes, sk: bytes) -> bytes:
            ss = ntru.decrypt(ct, sk)
            return ss

        return _encapsulate, _decapsulate
    except Exception as e:
        raise ImportError from e


def _load_pqcrypto() -> Tuple:
    """
    Fallback to `pqcrypto` package (pip install pqcrypto)
    """
    try:
        kem = importlib.import_module("pqcrypto.kem.ntruhrss701")  # type: ignore
        logger.info("Algorithm.core.crypto: using pqcrypto.ntruhrss701 back-end")

        def _encapsulate(pk: bytes) -> Tuple[bytes, bytes]:
            return kem.encrypt(pk)

        def _decapsulate(ct: bytes, sk: bytes) -> bytes:
            return kem.decrypt(ct, sk)

        return _encapsulate, _decapsulate
    except Exception as e:
        raise ImportError from e


# ---------------------------------------------------------------------------
# select back-end
# ---------------------------------------------------------------------------

_encapsulate: callable
_decapsulate: callable
_back_end: str

for _loader in (_load_ntrust_native, _load_pqcrypto):
    try:
        _encapsulate, _decapsulate = _loader()
        _back_end = _loader.__name__[6:]  # cosmetic
        break
    except ImportError:
        continue
else:
    raise ImportError(
        "No usable NTRU KEM back-end found. "
        "Install `ntrust_native_py` wheel or `pqcrypto` package."
    )

# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def wrap_key_ntru(pub_key: bytes, key: bytes) -> bytes:
    """
    Parameters
    ----------
    pub_key : bytes
        NTRU 公開鍵 (hrss-701, 930 bytes)
    key : bytes
        “包みたい” 任意の秘密鍵 (32-64 bytes 推奨)

    Returns
    -------
    capsule : bytes
        NTRU 暗号カプセル (1 136 bytes)
    """
    ct, ss = _encapsulate(pub_key)
    if len(ss) < len(key):
        raise ValueError("shared secret shorter than key to wrap")
    # XOR-mask でラップ (KDF を挟んでも良い)
    capsule = ct + bytes(k ^ s for k, s in zip(key, ss))
    return capsule


def unwrap_key_ntru(priv_key: bytes, capsule: bytes) -> bytes:
    """
    Parameters
    ----------
    priv_key : bytes
        NTRU 秘密鍵 (hrss-701, 1234 bytes)
    capsule : bytes
        wrap_key_ntru が返したバイト列

    Returns
    -------
    key : bytes
        復元した元の鍵
    """
    ct_len = 1136  # ntruhrss701 ciphertext length
    ct, masked = capsule[:ct_len], capsule[ct_len:]
    ss = _decapsulate(ct, priv_key)
    if len(masked) > len(ss):
        raise ValueError("capsule is malformed (masked part too long)")
    return bytes(m ^ s for m, s in zip(masked, ss))


__all__ = ["wrap_key_ntru", "unwrap_key_ntru"]
