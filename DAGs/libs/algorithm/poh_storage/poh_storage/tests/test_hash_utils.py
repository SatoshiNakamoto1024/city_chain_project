# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tests\test_hash_utils.py
import hashlib
from poh_storage.hash_utils import sha256_hex

def test_sha256_hex_empty():
    assert sha256_hex(b"") == hashlib.sha256(b"").hexdigest()
