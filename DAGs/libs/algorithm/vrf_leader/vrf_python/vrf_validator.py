# VRF/vrf_python/vrf_validator.py

"""VRF proof 検証ラッパー"""

import binascii
from typing import Union
from vrf_rust import verify_vrf_py

__all__ = ["verify_vrf"]

def _ensure_bytes(data: Union[bytes, bytearray, list[int]]) -> bytes:
    """
    Accepts bytes, bytearray, or list[int] and returns a bytes object.
    """
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, list):
        return bytes(data)
    raise TypeError(f"Expected bytes or list[int], got {type(data).__name__}")

def verify_vrf(public_key_hex: str, proof_hex: str, message: Union[str, bytes]) -> str:
    """
    VRF proof を検証し、hash を返す。

    Args:
        public_key_hex: 公開鍵の16進文字列
        proof_hex: proof の16進文字列
        message: bytes または str

    Returns:
        hash_hex

    Raises:
        RuntimeError if verification fails
    """
    pk = bytes.fromhex(public_key_hex)
    proof = bytes.fromhex(proof_hex)
    msg = message.encode() if isinstance(message, str) else message

    hash_raw = verify_vrf_py(pk, proof, msg)
    hash_out = _ensure_bytes(hash_raw)
    return hash_out.hex()
