# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\__init__.py
# -*- coding: utf-8 -*-
"""
PoH-Hold-Metrics Python API (lightweight)

Rust 製コアライブラリとの FFI バインディングおよび、
Python 側ユーティリティ群を提供します。
"""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("poh_holdmetrics")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["calculate_score", "AsyncTracker", "Scheduler", "__version__"]

def __getattr__(name):
    if name == "calculate_score":
        from .calculator import calculate_score
        return calculate_score
    if name == "AsyncTracker":
        from .tracker import AsyncTracker
        return AsyncTracker
    if name == "Scheduler":
        from .scheduler import Scheduler
        return Scheduler
    raise AttributeError(name)
