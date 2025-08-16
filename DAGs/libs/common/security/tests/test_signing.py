# network/DAGs/common/security/tests/test_signing.py
import pytest
import os, sys
sys.path.append(os.path.abspath("D:\\city_chain_project\\network\\DAGs\\common"))

from security import signing

@pytest.mark.parametrize("msg", [b"hello", b""])
def test_dilithium(msg):
    pk, sk = signing.create_dilithium_keypair()
    sig    = signing.sign_dilithium(msg, sk)
    assert signing.verify_dilithium(msg, sig, pk)

def test_ntru():
    pk, sk = signing.create_ntru_keypair()
    ct, ss = signing.encrypt_ntru(pk)
    ss2    = signing.decrypt_ntru(ct, sk)
    assert ss == ss2

def test_rsa():
    priv, pub = signing.create_rsa_keypair()
    msg       = b"rsa-message"
    sig       = signing.sign_rsa(msg, priv)
    assert signing.verify_rsa(msg, sig, pub)
