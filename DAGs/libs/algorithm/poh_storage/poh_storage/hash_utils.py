# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\hash_utils.py
import hashlib


def sha256_hex(data: bytes) -> str:
    """
    Compute SHA-256 and return hex digest.
    """
    return hashlib.sha256(data).hexdigest()
