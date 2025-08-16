# D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\rvh_stable\stable.py
"""
Jump Consistent Hash
====================

Google Cloud Blog (2014) 掲載のアルゴリズムを純 Python で実装。

- sync:  jump_hash(key: int, buckets: int) -> int
- async: async_jump_hash(key: int, buckets: int) -> int
"""

"""
rvh_stable: Jump Hash (Google Jump Consistent Hash) の純粋 Python 実装
"""

import struct
import logging

def jump_hash(key: str, buckets: int) -> int:
    """
    春菅の Jump Consistent Hash アルゴリズム実装
    Args:
        key: 任意の文字列
        buckets: 正の整数バケット数
    Returns:
        0 <= shard < buckets
    """
    if buckets < 1:
        raise ValueError("buckets must be >= 1")
    # 64bit ハッシュ化には FNV-1a でもよいし、ここでは組み込み hash を利用
    h = hash(key) & 0xFFFFFFFFFFFFFFFF
    b = -1
    j = 0
    while j < buckets:
        b = j
        # LCG で擬似乱数を 64bit 更新
        h = (h * 2862933555777941757 + 1) & 0xFFFFFFFFFFFFFFFF
        # next bucket の計算
        j = int((b + 1) * (1 << 31) / ((h >> 33) + 1))
    return b

async def async_jump_hash(key: str, buckets: int) -> int:
    """
    非同期版。CPU バウンドなので、デフォルトではスレッドプールで実行。
    """
    import asyncio
    loop = asyncio.get_running_loop()
    # sync 関数を別スレッドで実行
    return await loop.run_in_executor(None, jump_hash, key, buckets)
