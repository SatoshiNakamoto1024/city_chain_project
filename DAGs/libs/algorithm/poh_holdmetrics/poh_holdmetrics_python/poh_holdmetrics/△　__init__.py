# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\__init__.py
# -*- coding: utf-8 -*-
"""
PoH-Hold-Metrics Python API (lightweight)

Rust 製コアライブラリとの FFI バインディングおよび、
Python 側ユーティリティ群を提供します。
"""

from importlib.metadata import version, PackageNotFoundError

from .calculator import calculate_score
from .tracker import AsyncTracker
from .scheduler import Scheduler

try:
    __version__ = version("poh_holdmetrics")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "AsyncTracker",
    "Scheduler",
    "__version__",
    "calculate_score",
]
