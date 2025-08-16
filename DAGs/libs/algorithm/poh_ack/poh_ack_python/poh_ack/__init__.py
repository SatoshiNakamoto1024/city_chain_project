# D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_python\poh_ack\__init__.py

from .models import AckRequest, AckResult
from .verifier import verify_ack, verify_ack_async
from .cli import cli  # Click Group
from importlib import import_module

# ① Rust 拡張を最初に読み込む
_rust = import_module("poh_ack_rust")   # PyInit が呼ばれて GIL 初期化

# ② ここから後は自由に外部 C-ext を import しても安全
from ._version import __version__

__all__ = [
    "__version__",
    "AckRequest",
    "AckResult",
    "verify_ack",
    "verify_ack_async",
    "cli",
]
