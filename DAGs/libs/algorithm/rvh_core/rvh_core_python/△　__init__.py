# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_python\__init__.py
"""
rvh_python
==========

Rendezvous-Hash (Highest-Random-Weight) の Python ラッパー・モジュール。

- Rust 実装（`rvh_rust`）がインストールされていれば高速版を自動利用
- Rust が無い環境でも pure-Python フォールバックを提供
"""

from .rvh_builder import rendezvous_hash, RVHError
from ._version import __version__

__all__ = [
    "RVHError",
    "__version__",
    "rendezvous_hash",
]
