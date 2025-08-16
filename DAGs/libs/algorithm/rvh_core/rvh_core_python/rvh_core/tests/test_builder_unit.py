# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\tests\test_builder_unit.py

"""Unit-tests focusing on pure-Python implementation only."""
import hashlib
from random import Random
import os
os.environ["RVH_FORCE_PYTHON"] = "1"   # ← 最優先で設定
from rvh_core import rendezvous_hash

def _reference(nodes, key, k):
    key_b = key.encode()
    scores = []
    for n in nodes:
        h = hashlib.blake2b(digest_size=16)   # BLAKE2b-128
        h.update(key_b)                      # key → node 順
        h.update(n.encode())
        digest = h.digest()                  # 16 byte
        score = int.from_bytes(digest, "little")  # little-endian
        scores.append((score, n))

    # Rust と同じ並べ替え：スコア↓・ノード↓
    scores.sort(key=lambda t: (t[0], t[1]), reverse=True)
    selected = [n for _, n in scores[:k]]
    print(f"REFERENCE selected: {selected}")
    return selected


def test_matches_reference():
    nodes = [f"n{i}" for i in range(10)]
    key = "obj-1"
    for k in range(1, 6):
        assert rendezvous_hash(nodes, key, k) == _reference(nodes, key, k)


def test_random_fuzz():
    rnd = Random(0)
    for _ in range(100):
        n = rnd.randint(3, 15)
        nodes = [f"node{rnd.randrange(1000)}" for _ in range(n)]
        key = f"obj{rnd.randrange(10000)}"
        k = rnd.randint(1, n)
        assert rendezvous_hash(nodes, key, k) == _reference(nodes, key, k)
