# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python/__init__.py

"""
rvh_faultset: GeoHash ベースのレイテンシ最適化 ＋ Rust failover 統合パイプライン

Pure-Python で Geohash クラスタリングを行い、
その後 Rust コアの failover() を呼び出します。
"""

"""
rvh_faultset: GeoHash ベースのレイテンシ最適化 ＋ Rust failover 統合パイプライン

Pure-Python で Geohash クラスタリングを行い、
その後 Rust コアの failover() を呼び出します。
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("rvh_faultset")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = ("faultset", "faultset_async", "FaultsetError", "__version__")
