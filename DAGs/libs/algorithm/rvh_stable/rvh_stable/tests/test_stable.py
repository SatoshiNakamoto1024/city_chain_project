# D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\rvh_stable\tests\test_stable.py
import pytest
import asyncio

from rvh_stable import jump_hash, async_jump_hash


@pytest.mark.parametrize("key,buckets,expected", [
    (0, 1, 0),
    (1, 1, 0),
    (123456, 5, jump_hash(123456, 5)),  # idempotent
])
def test_jump_hash_sync(key, buckets, expected):
    assert jump_hash(key, buckets) == expected


def test_jump_hash_changes_with_buckets():
    k = 98765
    a = jump_hash(k, 3)
    b = jump_hash(k, 4)
    assert 0 <= a < 3
    assert 0 <= b < 4
    # 3→4 にバケット数を増やせば必ず同じになるわけではない
    assert a != b


@pytest.mark.asyncio
async def test_jump_hash_async():
    k, n = 42, 10
    s1 = await async_jump_hash(k, n)
    s2 = await async_jump_hash(k, n)
    assert s1 == s2
    assert 0 <= s1 < n


def test_invalid_buckets():
    with pytest.raises(ValueError):
        jump_hash(10, 0)

    import pytest as _pytest
    with _pytest.raises(ValueError):
        asyncio.run(async_jump_hash(10, 0))
