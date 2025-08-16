# D:\city_chain_project\network\DAGs\common\errors\policies.py
"""
policies.py  ― 例外種別 → ポリシーマッピング
環境変数で上書きできるようにしておくと運用が楽。
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Mapping, Type
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from errors.exceptions import (
    BaseError,
    NetworkError,
    StorageError,
    ValidationError,
    SecurityError,
)

__all__ = ["AlertLevel", "ErrorPolicy", "get_policy"]


class AlertLevel(Enum):
    NONE = auto()
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass(slots=True)
class ErrorPolicy:
    """リトライ・バックオフ・通知レベル"""

    max_attempts: int = 0               # 0 = リトライなし
    initial_backoff: float = 0.0        # 秒
    alert_level: AlertLevel = AlertLevel.INFO

    def merge_env(self, prefix: str) -> "ErrorPolicy":
        """
        環境変数 ``{prefix}_MAX`` / ``{prefix}_BACKOFF`` / ``{prefix}_ALERT``
        で上書き出来るようにする。
        """
        max_env = os.getenv(f"{prefix}_MAX")
        back_env = os.getenv(f"{prefix}_BACKOFF")
        alert_env = os.getenv(f"{prefix}_ALERT")

        return ErrorPolicy(
            max_attempts=int(max_env) if max_env else self.max_attempts,
            initial_backoff=float(back_env) if back_env else self.initial_backoff,
            alert_level=AlertLevel[alert_env] if alert_env else self.alert_level,
        )


# デフォルトマップ
_POLICIES: Mapping[Type[BaseError], ErrorPolicy] = {
    NetworkError: ErrorPolicy(max_attempts=3, initial_backoff=0.1, alert_level=AlertLevel.WARNING),
    StorageError: ErrorPolicy(max_attempts=5, initial_backoff=0.2, alert_level=AlertLevel.CRITICAL),
    ValidationError: ErrorPolicy(max_attempts=0, initial_backoff=0.0, alert_level=AlertLevel.NONE),
    SecurityError: ErrorPolicy(max_attempts=0, initial_backoff=0.0, alert_level=AlertLevel.CRITICAL),
}


def get_policy(exc: BaseError | type[BaseError]) -> ErrorPolicy:
    """
    例外インスタンス or クラス → ErrorPolicy
    環境変数で個別上書きがあれば取り込む
    """
    cls = exc if isinstance(exc, type) else exc.__class__
    pol = _POLICIES.get(cls, ErrorPolicy())   # デフォルト
    return pol.merge_env(prefix=cls.__name__.upper())
