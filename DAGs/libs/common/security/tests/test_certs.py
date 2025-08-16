# network/DAGs/common/security/tests/test_certs.py
import pytest
import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import os, sys
sys.path.append(os.path.abspath("D:\\city_chain_project\\network\\DAGs\\common"))

from security import certs

def generate_self_signed(tmp_path):
    # 鍵ペア生成
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Subject/Issuer
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.local")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    p = tmp_path / "cert.pem"
    p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return p

def test_load_and_cn(tmp_path):
    p = generate_self_signed(tmp_path)
    c = certs.load_pem_cert(str(p))
    assert isinstance(c, x509.Certificate)
    assert certs.get_cn(c) == "test.local"

def test_validate_chain(tmp_path):
    p = generate_self_signed(tmp_path)
    c = certs.load_pem_cert(str(p))
    # self-signed なので trust_anchors に自身を渡せば True
    assert certs.validate_chain(c, [c]) is True
