# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\__init__.py
"""
poh_storage: PoH transaction persistence and recovery
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("poh_storage")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

# Public API
from .storage import StorageManager

__all__ = ("StorageManager", "__version__")
