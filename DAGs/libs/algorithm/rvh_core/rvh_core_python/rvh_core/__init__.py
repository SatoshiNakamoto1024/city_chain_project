# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\__init__.py
"""
rvh_core – Python フロントエンド

* Rust 拡張 (rvh_core_rust) が入っていれば自動利用
* ない場合は pure-Python 実装でフォールバック
"""

from .rvh_builder import (
    rendezvous_hash,
    arendezvous_hash,
    RVHError,
)
from ._version import __version__

__all__ = [
    "RVHError",
    "__version__",
    "arendezvous_hash",
    "rendezvous_hash",
]
