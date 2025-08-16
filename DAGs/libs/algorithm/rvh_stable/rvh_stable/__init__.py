# D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\rvh_stable\__init__.py
"""
rvh_stable: Pure-Python Jump Consistent Hash (sync + async)
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("rvh_stable")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

from .stable import jump_hash, async_jump_hash

__all__ = ("jump_hash", "async_jump_hash", "__version__")
