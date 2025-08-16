# network/DAGs/common/security/tests/test_encryption.py
import pytest
import os, sys
sys.path.append(os.path.abspath("D:\\city_chain_project\\network\\DAGs\\common"))

from security import encryption

def test_encrypt_decrypt_field():
    key = encryption.AESGCM.generate_key(bit_length=256)
    pt  = b"secret data"
    ct  = encryption.encrypt_field(pt, key)
    pt2 = encryption.decrypt_field(ct, key)
    assert pt2 == pt

def test_create_data_key():
    kid, key = encryption.create_data_key()
    assert isinstance(kid, str) and isinstance(key, bytes)
