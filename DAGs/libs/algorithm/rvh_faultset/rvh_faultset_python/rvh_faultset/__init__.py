# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\rvh_faultset\__init__.py
"""
rvh_faultset: GeoHash によるレイテンシ・クラスタリング＋Rust failover 統合パイプライン

Pure-Python で geohash クラスタリングを行い、その後 Rust コアの failover() を呼び出します。
"""

"""
rvh_faultset: GeoHash によるレイテンシ・クラスタリング＋Rust failover 統合パイプライン

Pure-Python で geohash クラスタリングを行い、その後 Rust コアの failover() を呼び出します。
"""

from importlib.metadata import version, PackageNotFoundError

# パッケージ・バージョン (pyproject.toml の [project].version を同期)
try:
    __version__ = version("rvh_faultset")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

# 公開 API
from .faultset_builder import faultset, faultset_async, FaultsetError

__all__ = ("FaultsetError", "__version__", "faultset", "faultset_async")
