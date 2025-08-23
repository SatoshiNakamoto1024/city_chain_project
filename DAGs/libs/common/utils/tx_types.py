# network/DAGs/common/utils/tx_types.py
"""
TxType 列挙型
=============
フェデレーション全体で扱うトランザクションタイプを定義。
"""

from __future__ import annotations
from enum import Enum


class TxType(Enum):
    """サポートするトランザクションの種別"""

    TRANSFER = "TRANSFER"           # 単純送金
    CONTRACT_CALL = "CONTRACT_CALL"  # スマコン呼び出し
    STAKE = "STAKE"                 # ステーキング
    UNSTAKE = "UNSTAKE"             # ステーキング解除
    VOTE = "VOTE"                   # 投票
    # 必要なら以下に追加してください

    @classmethod
    def has_value(cls, value: str) -> bool:
        """
        指定文字列が有効な TxType かチェックする。

        >>> TxType.has_value("TRANSFER")
        True
        >>> TxType.has_value("UNKNOWN")
        False
        """
        return value in cls._value2member_map_
