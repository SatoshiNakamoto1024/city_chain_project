# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\compression.py
"""
compression.py
==============

ACK バッチを保存する際の **汎用圧縮ユーティリティ**。

サポート codec
    * **zstd** … `zstandard` がインストールされている場合のみ有効
    * **gzip** … Python 標準ライブラリ (Fallback)

公開 API
    compress(data: bytes, level: int = 3) -> tuple[str, bytes]
        `(codec, compressed_data)` を返す。zstd 優先。
    decompress(codec: str, data: bytes) -> bytes
        codec を指定して伸張する。
"""

from __future__ import annotations

import gzip
import importlib.util
from typing import Final, Tuple

# ------------------------------------------------------------
# オプション依存 (zstandard)
# ------------------------------------------------------------
_ZSTD_AVAILABLE: Final[bool] = importlib.util.find_spec("zstandard") is not None
if _ZSTD_AVAILABLE:
    import zstandard as _zstd


# ------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------
__all__ = ["compress", "decompress"]


def compress(data: bytes, level: int = 3) -> Tuple[str, bytes]:
    """
    **data** を圧縮して `(codec, bytes)` を返す。

    Parameters
    ----------
    data : bytes
        元データ
    level : int, default 3
        圧縮レベル
        *gzip* : 1–9
        *zstd* : 1–22 (3 は zstd のデフォルトに相当)

    Returns
    -------
    tuple[str, bytes]
        - codec: ``"zstd"`` または ``"gzip"``
        - compressed bytes
    """
    if _ZSTD_AVAILABLE:
        cctx = _zstd.ZstdCompressor(level=level)  # type: ignore[attr-defined]
        return "zstd", cctx.compress(data)

    return "gzip", gzip.compress(data, compresslevel=level)


def decompress(codec: str, data: bytes) -> bytes:
    """
    codec を指定して伸張。

    Raises
    ------
    RuntimeError
        *codec == "zstd"* だが `zstandard` が import 不能
    ValueError
        未知 codec を指定
    """
    if codec == "zstd":
        if not _ZSTD_AVAILABLE:
            raise RuntimeError("codec zstd requested but 'zstandard' package not installed")
        dctx = _zstd.ZstdDecompressor()  # type: ignore[attr-defined]
        return dctx.decompress(data)

    if codec == "gzip":
        return gzip.decompress(data)

    raise ValueError(f"unknown codec: {codec!r}")
