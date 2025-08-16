"""
ライトノードの 100 MB キャッシュ (2 KB/Tx 想定) を LRU でシミュレーション
"""
from cachetools import LRUCache
CACHE_SIZE = 100 * 1024 * 1024 // 2048  # ≒ 50 000 Tx
node_cache = LRUCache(maxsize=CACHE_SIZE)
