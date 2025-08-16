# VRF/vrf_python/test_vrf.py
import binascii
import pytest
from .vrf_builder import generate_keypair, prove_vrf 
from .vrf_validator import verify_vrf


def test_roundtrip():
    # Generate keys
    pub_hex, priv_hex = generate_keypair()
    msg = b"hello vrf"

    # Produce proof and hash
    proof_hex, hash1 = prove_vrf(priv_hex, msg)

    # Verify and get the same hash back
    hash2 = verify_vrf(pub_hex, proof_hex, msg)
    assert hash1 == hash2, "Mismatch in VRF hash roundtrip"


def test_bad_proof():
    pub_hex, priv_hex = generate_keypair()
    msg = b"test bad proof"

    # Create a valid proof then tamper
    proof_hex, _ = prove_vrf(priv_hex, msg)
    proof_bytes = bytearray.fromhex(proof_hex)
    proof_bytes[0] ^= 0xFF
    bad_proof_hex = proof_bytes.hex()

    # Verification should error
    with pytest.raises(Exception):
        verify_vrf(pub_hex, bad_proof_hex, msg)