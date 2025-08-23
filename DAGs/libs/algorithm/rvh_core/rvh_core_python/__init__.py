# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\__init__.py
"""Top-level re-export for convenience."""
from importlib import metadata as _md

# rvh_core サブパッケージから API を引き上げる
from .rvh_core import (
    rendezvous_hash,
    arendezvous_hash,
    RVHError,
)

try:
    __version__ = _md.version(__name__)
except _md.PackageNotFoundError:                       # dev 環境
    from .rvh_core import _version as _v
    __version__ = _v.__version__

__all__ = [
    "RVHError",
    "__version__",
    "arendezvous_hash",
    "rendezvous_hash",
]
