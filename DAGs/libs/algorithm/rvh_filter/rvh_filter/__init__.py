# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\__init__.py

from __future__ import annotations

"""
rvh_filter
==========

ブラックリスト・正規表現・述語関数で
ノード一覧をフィルタリングするユーティリティ。
同期／非同期 API を提供します。
"""

# バージョン情報
from importlib.metadata import version as _version, PackageNotFoundError

try:
    __version__ = _version(__name__)
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

# 公開 API
from .filter_core import (
    filter_nodes,
    filter_nodes_async,
    NodeFilter,
    AsyncNodeFilter,
    FilterError,
)

__all__ = (
    "AsyncNodeFilter",
    "FilterError",
    "NodeFilter",
    "__version__",
    "filter_nodes",
    "filter_nodes_async",
)
