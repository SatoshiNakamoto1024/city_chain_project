# sending_DAG/python_sending/cert_python/loader.py
import pathlib, re

PEM_PRIV_TAG = re.compile(r"-----BEGIN (?P<alg>.+) PRIVATE KEY-----(?P<b64>.+?)-----END", re.S)
PEM_PUB_TAG  = re.compile(r"-----BEGIN (?P<alg>.+) PUBLIC KEY-----(?P<b64>.+?)-----END",  re.S)


def _b64_to_hex(b64_str: str) -> str:
    import base64, binascii
    return binascii.hexlify(base64.b64decode(b64_str.encode())).decode()


def load_pem_cert(path: str|pathlib.Path) -> dict:
    text = pathlib.Path(path).read_text()
    priv_m = PEM_PRIV_TAG.search(text)
    pub_m  = PEM_PUB_TAG.search(text)
    if not priv_m or not pub_m:
        raise ValueError(f"Invalid PEM file: {path}")

    return {
        "alg": priv_m["alg"].strip(),
        "priv_hex": _b64_to_hex(priv_m["b64"].strip()),
        "pub_hex":  _b64_to_hex(pub_m["b64"].strip()),
    }


def get_private_key_hex(pem_path: str|pathlib.Path) -> str:
    return load_pem_cert(pem_path)["priv_hex"]


def get_public_key_hex(pem_path: str|pathlib.Path) -> str:
    return load_pem_cert(pem_path)["pub_hex"]