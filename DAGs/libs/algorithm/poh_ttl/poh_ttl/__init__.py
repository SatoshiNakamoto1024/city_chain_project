# D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\poh_ttl\__init__.py
"""
poh_ttl: PoH transaction TTL manager.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("poh_ttl")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

# Public API
from poh_storage.storage import StorageManager

__all__ = ("StorageManager", "__version__")
