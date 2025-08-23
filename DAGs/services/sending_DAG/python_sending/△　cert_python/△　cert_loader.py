# sending_DAG/python_sending/cert_python/cert_loader.py
"""
PEM (独自CA発行) を読み込んで公開鍵・秘密鍵 HEX を返す簡易ユーティリティ
※ Dilithium/NTRU 部分はダミー実装
"""
import pathlib
import re

PEM_PRIV_TAG = re.compile(r"-----BEGIN (?P<alg>.+) PRIVATE KEY-----(?P<b64>.+?)-----END", re.S)
PEM_PUB_TAG = re.compile(r"-----BEGIN (?P<alg>.+) PUBLIC KEY-----(?P<b64>.+?)-----END", re.S)


def _b64_to_hex(b64_str: str) -> str:
    import base64
    import binascii
    return binascii.hexlify(base64.b64decode(b64_str.encode())).decode()


def load_pem_cert(path: str | pathlib.Path) -> dict:
    text = pathlib.Path(path).read_text()
    priv_m = PEM_PRIV_TAG.search(text)
    pub_m = PEM_PUB_TAG.search(text)
    if not priv_m or not pub_m:
        raise ValueError("Invalid PEM file")

    return {
        "alg": priv_m["alg"].strip(),
        "priv_hex": _b64_to_hex(priv_m["b64"].strip()),
        "pub_hex": _b64_to_hex(pub_m["b64"].strip()),
    }


def get_private_key_hex(pem_path: str) -> str:
    return load_pem_cert(pem_path)["priv_hex"]


def get_public_key_hex(pem_path: str) -> str:
    return load_pem_cert(pem_path)["pub_hex"]
