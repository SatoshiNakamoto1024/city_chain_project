# VRF/vrf_python/vrf_builder.py
from typing import Union
from vrf_rust import generate_vrf_keypair_py, prove_vrf_py, verify_vrf_py

__all__ = ["generate_keypair", "prove_vrf", "verify_vrf"]


def _ensure_bytes(data: Union[bytes, bytearray, list[int]]) -> bytes:
    """
    Accepts bytes, bytearray, or list[int] and returns a bytes object.
    """
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, list):
        return bytes(data)
    raise TypeError(f"Expected bytes or list[int], got {type(data).__name__}")


def generate_keypair() -> tuple[str, str]:
    """
    Generate a VRF keypair (P-256 + ECVRF) and return hex-encoded strings.

    Returns:
        (public_key_hex, secret_key_hex)
    """
    pk_raw, sk_raw = generate_vrf_keypair_py()
    pk = _ensure_bytes(pk_raw)
    sk = _ensure_bytes(sk_raw)
    return pk.hex(), sk.hex()


def prove_vrf(secret_key_hex: str, message: Union[str, bytes]) -> tuple[str, str]:
    """
    Produce a VRF proof and output hash for a given message.

    Args:
        secret_key_hex: Secret key in hex string
        message: bytes or str to be proven

    Returns:
        (proof_hex, hash_output_hex)
    """
    sk = bytes.fromhex(secret_key_hex)
    msg = message.encode() if isinstance(message, str) else message

    proof_raw, hash_raw = prove_vrf_py(sk, msg)
    proof = _ensure_bytes(proof_raw)
    hash_out = _ensure_bytes(hash_raw)
    return proof.hex(), hash_out.hex()


def verify_vrf(public_key_hex: str, proof_hex: str, message: Union[str, bytes]) -> str:
    """
    Verify a VRF proof and return the hash output if valid.

    Args:
        public_key_hex: Public key in hex string
        proof_hex: VRF proof in hex string
        message: bytes or str that was proven

    Returns:
        hash_output_hex

    Raises:
        RuntimeError: if proof verification fails
    """
    pk = bytes.fromhex(public_key_hex)
    proof = bytes.fromhex(proof_hex)
    msg = message.encode() if isinstance(message, str) else message

    hash_raw = verify_vrf_py(pk, proof, msg)
    hash_out = _ensure_bytes(hash_raw)
    return hash_out.hex()
