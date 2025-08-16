# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\__init__.py
# poh_request/__init__.py
from importlib.metadata import PackageNotFoundError, version

from .builder import PoHRequestBuilder
from .exceptions import EncodeError, PoHRequestError, SendError
from .schema import PoHRequest, PoHResponse
from .sender import AsyncSender, send, send_sync      # ★ send を追加

__all__ = [
    "PoHRequest",
    "PoHResponse",
    "PoHRequestBuilder",
    "AsyncSender",
    "send",            # ★
    "send_sync",
    "PoHRequestError",
    "EncodeError",
    "SendError",
]

try:
    __version__ = version("poh_request")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

# --------------------------------------------------------------------- #
# 互換エイリアス ― tests が ``import poh_request.poh_request`` を期待
# --------------------------------------------------------------------- #
import sys, types

_alias = types.ModuleType(f"{__name__}.{__name__}")
_alias.__dict__.update(globals())               # ルート名前空間を丸ごと共有
sys.modules[_alias.__name__] = _alias           # → import succeeds
