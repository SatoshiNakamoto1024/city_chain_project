# sending_dapps/cert_cache.py
"""
cert_cache.py
─────────────────────────────────────────────
• ルート CA 情報のワンタイムロード
• PEM → 検証済み bool  の LRU + TTL キャッシュ
• NTRU ciphertext → shared_secret  の LRU キャッシュ
"""

from __future__ import annotations
import time, functools, hashlib
from typing import Callable, Any
from collections import OrderedDict

# ─── キャッシュ設定 ─────────────────────────────────────
CERT_TTL_SEC     = 300          # 証明書検証結果 5 分キャッシュ
CERT_CACHE_SIZE  = 512
NTRU_CACHE_SIZE  = 1024

class _TTLCache(OrderedDict):
    """簡易 TTL 付き LRU"""
    def __init__(self, maxlen: int, ttl: int):
        super().__init__()
        self.maxlen = maxlen
        self.ttl    = ttl
    def __getitem__(self, k):
        v, t = super().__getitem__(k)
        if time.time() - t > self.ttl:
            del self[k];  raise KeyError
        self.move_to_end(k)
        return v
    def __setitem__(self, k, v):
        if k in self:       del self[k]
        elif len(self) >= self.maxlen:
            self.popitem(last=False)
        super().__setitem__(k, (v, time.time()))

_cert_cache = _TTLCache(CERT_CACHE_SIZE, CERT_TTL_SEC)
_ntru_cache = OrderedDict()               # サイズだけ見る LRU

def cached_verify(fn: Callable[[bytes], bool]) -> Callable[[bytes], bool]:
    """PEM → bool キャッシュデコレータ"""
    @functools.wraps(fn)
    def wrapper(pem: bytes) -> bool:
        h = hashlib.sha256(pem).digest()
        try:   return _cert_cache[h]
        except KeyError:
            r = fn(pem)
            _cert_cache[h] = r
            return r
    return wrapper

def get_cached_secret(cipher: bytes) -> bytes | None:
    k = hashlib.sha256(cipher).digest()
    try:
        _ntru_cache.move_to_end(k);  return _ntru_cache[k]
    except KeyError:
        return None

def put_cached_secret(cipher: bytes, secret: bytes):
    k = hashlib.sha256(cipher).digest()
    if k in _ntru_cache:  del _ntru_cache[k]
    elif len(_ntru_cache) >= NTRU_CACHE_SIZE:
        _ntru_cache.popitem(last=False)
    _ntru_cache[k] = secret
