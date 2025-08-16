# D:\city_chain_project\rvh_trace_python\__init__.py

"""
rvh_faultset: GeoHash ベースのレイテンシ最適化 ＋ Rust failover 統合パイプライン

Pure-Python で Geohash クラスタリングを行い、
その後 Rust コアの failover() を呼び出します。
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("rvh_faultset_python")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = ("faultset", "__version__")
