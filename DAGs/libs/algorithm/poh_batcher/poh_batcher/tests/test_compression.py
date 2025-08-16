# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\tests\test_compression.py
"""
test_compression.py
===================

圧縮ユーティリティのラウンドトリップ & 不正 codec 検証
"""

import os
import random
import string

import pytest

from poh_batcher.compression import _ZSTD_AVAILABLE, compress, decompress


@pytest.mark.parametrize("size", [0, 10, 128 * 1024])
def test_roundtrip(size: int) -> None:
    data = os.urandom(size) if size else b""
    codec, blob = compress(data, level=5)
    roundtrip = decompress(codec, blob)
    assert roundtrip == data

    # gzip フォールバック経路も確実にテスト
    if _ZSTD_AVAILABLE and codec == "zstd":
        codec_gz, blob_gz = ("gzip", compress(data, level=4)[1])
        assert decompress(codec_gz, blob_gz) == data


def test_unknown_codec() -> None:
    with pytest.raises(ValueError):
        decompress("unknown_codec", b"123")


def test_zstd_required() -> None:
    """
    zstandard 未インストール環境で zstd を要求した場合の RuntimeError。
    （実際には tox などで zstandard をアンインストールした job を用意）
    """
    if _ZSTD_AVAILABLE:
        pytest.skip("zstandard installed — test not applicable")

    with pytest.raises(RuntimeError):
        decompress("zstd", b"dummy")
