# D:\city_chain_project\network\sending_DAGs\python_sending\common\__init__.py
"""
common パッケージ

上位コードから::

    import common as C
    C.config.MIN_BATCH_INTERVAL
    C.db.save_completed_tx_to_mongo({...})

のように使えるよう再エクスポートしている。
"""
from __future__ import annotations
from importlib import import_module
from typing import TYPE_CHECKING, Any

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ─────────────────────────────────────────────────────────────
# 再エクスポート対象モジュール名
# ─────────────────────────────────────────────────────────────
__all_modules = (
    "config",
    "db_handler",
    "distributed_storage_system",
    "node_registry",
    "reward_system",
    "rebalancer",
)

# 動的 import して globals に登録
for _m in __all_modules:
    globals()[_m] = import_module(f"{__name__}.{_m}")

# __all__ も整備
__all__: list[str] = list(__all_modules)

if TYPE_CHECKING:  # mypy / IDE 用型ヒント
    import common.config as config
    import common.db_handler as db_handler
    import common.distributed_storage_system as distributed_storage_system
    import common.node_registry as node_registry
    import common.reward_system as reward_system
    import common.rebalancer as rebalancer
