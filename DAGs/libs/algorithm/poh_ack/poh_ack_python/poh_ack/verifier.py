# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\verifier.py

import asyncio
from datetime import datetime, timezone, timedelta

import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from .models import AckRequest, AckResult

# Rust 拡張モジュールがあれば非同期版を利用
try:
    import poh_ack_rust as _rust
    _HAVE_RUST = True
except ImportError:
    _HAVE_RUST = False


def _canonical_payload(id: str, timestamp: str) -> bytes:
    """
    Rust 側と同様の canonical JSON を生成
    {"id":"...","timestamp":"..."}
    """
    s = f'{{"id":"{id}","timestamp":"{timestamp}"}}'
    return s.encode("utf-8")


def verify_ack(req: AckRequest, ttl_seconds: int) -> AckResult:
    """
    同期的に ACK を検証 (Rust or Pure‑Python fallback)
    """
    if _HAVE_RUST:
        rust_ack = _rust.Ack(req.id, req.timestamp, req.signature, req.pubkey)
        try:
            rust_ack.verify(ttl_seconds)
            return AckResult(id=req.id, valid=True)
        except Exception as e:
            return AckResult(id=req.id, valid=False, error=str(e))
    else:
        return _verify_fallback(req, ttl_seconds)


async def verify_ack_async(req: AckRequest, ttl_seconds: int) -> AckResult:
    """
    非同期に ACK を検証 (Rust async or Pure‑Python fallback)
    """
    if _HAVE_RUST:
        rust_ack = _rust.Ack(req.id, req.timestamp, req.signature, req.pubkey)
        try:
            await rust_ack.verify_async(ttl_seconds)
            return AckResult(id=req.id, valid=True)
        except Exception as e:
            return AckResult(id=req.id, valid=False, error=str(e))
    else:
        return await asyncio.to_thread(_verify_fallback, req, ttl_seconds)


def _verify_fallback(req: AckRequest, ttl_seconds: int) -> AckResult:
    """
    Pure‑Python 版検証:
      1) TTL チェック
      2) Ed25519 署名検証 (cryptography)
    """
    # 1) TTL
    try:
        ts = datetime.fromisoformat(req.timestamp)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if ts + timedelta(seconds=ttl_seconds) < now:
            return AckResult(id=req.id, valid=False, error="TTL expired")
    except Exception as e:
        return AckResult(id=req.id, valid=False, error=f"invalid timestamp: {e}")

    # 2) 署名検証
    try:
        pk_bytes = base58.b58decode(req.pubkey)
        sig_bytes = base58.b58decode(req.signature)
        pubkey = Ed25519PublicKey.from_public_bytes(pk_bytes)
        pubkey.verify(sig_bytes, _canonical_payload(req.id, req.timestamp))
        return AckResult(id=req.id, valid=True)
    except InvalidSignature:
        return AckResult(id=req.id, valid=False, error="signature verification failed")
    except Exception as e:
        return AckResult(id=req.id, valid=False, error=f"verification error: {e}")
