# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\__init__.py

from __future__ import annotations

"""
rvh_filter
==========

ブラックリスト・正規表現・述語関数で “除外したいノード” をフィルタリングする
軽量ユーティリティライブラリです。

特長
----

- 依存ゼロ（標準ライブラリのみ）
- ワンライナーで使える：filter_nodes(nodes, blacklist=...)
- OO（オブジェクト指向）ラッパーも提供：NodeFilterクラス

使用例
------

>>> from rvh_filter import filter_nodes
>>> nodes = ["edge-1", "edge-2", "validator-1", "bad-node"]
>>> filter_nodes(nodes, blacklist={"bad-node"})
['edge-1', 'edge-2', 'validator-1']
"""

# バージョン情報の取得（PEP 396 準拠）
from importlib.metadata import version as _version, PackageNotFoundError

try:
    __version__: str = _version(__name__)
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

# 公開API
from .filter_core import (
    filter_nodes,
    NodeFilter,
    FilterError,
)

__all__: tuple[str, ...] = (
    "filter_nodes",
    "NodeFilter",
    "FilterError",
    "__version__",
)
