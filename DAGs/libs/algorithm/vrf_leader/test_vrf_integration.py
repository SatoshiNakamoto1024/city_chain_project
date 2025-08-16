# Algorithm/VRF/test_vrf_integration.py
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent))
print("sys.path =", sys.path)
import vrf_python
print("vrf_python imported:", vrf_python)
import binascii
import pytest

from vrf_python.vrf_builder import generate_keypair, prove_vrf
from vrf_python.vrf_validator import verify_vrf

def test_end_to_end_roundtrip():
    """
    完全なエンドツーエンド検証。
    1) 鍵ペア生成
    2) メッセージに対する証明とハッシュ生成
    3) 同じハッシュが返ることを検証
    """
    # 1) キーペア生成
    pub_hex, priv_hex = generate_keypair()
    msg = b"integration test message"

    # 2) 証明とハッシュ取得
    proof_hex, hash1 = prove_vrf(priv_hex, msg)

    # 3) 検証して同じハッシュが返ること
    hash2 = verify_vrf(pub_hex, proof_hex, msg)
    assert hash1 == hash2, "Round-trip VRF hash mismatch"

def test_integration_negative_tampered_proof():
    """
    証明を改ざんした場合に検証が失敗することを確認。
    """
    pub_hex, priv_hex = generate_keypair()
    msg = b"bad proof test"

    # 正しい証明を生成
    proof_hex, _ = prove_vrf(priv_hex, msg)

    # 証明をバイト列に戻し、先頭バイトを反転して改ざん
    proof_bytes = binascii.unhexlify(proof_hex)
    tampered = bytes([proof_bytes[0] ^ 0xFF]) + proof_bytes[1:]
    tampered_hex = binascii.hexlify(tampered).decode()

    # 検証時に RuntimeError が発生する
    with pytest.raises(RuntimeError):
        verify_vrf(pub_hex, tampered_hex, msg)

def test_integration_negative_wrong_pubkey():
    """
    別の公開鍵で同じ証明を検証しようとして失敗することを確認。
    """
    pub1, priv_hex = generate_keypair()
    pub2, _ = generate_keypair()
    msg = b"wrong pubkey test"

    proof_hex, _ = prove_vrf(priv_hex, msg)

    # pub2 で検証するとエラー
    with pytest.raises(RuntimeError):
        verify_vrf(pub2, proof_hex, msg)

def test_integration_string_message_support():
    """
    文字列メッセージでも動作することを確認。
    """
    pub_hex, priv_hex = generate_keypair()
    msg_str = "これはテスト文字列です。"

    proof_hex, hash1 = prove_vrf(priv_hex, msg_str)
    hash2 = verify_vrf(pub_hex, proof_hex, msg_str)
    assert hash1 == hash2, "String-message VRF hash mismatch"
