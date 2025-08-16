# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\filter_core.py
"""
filter_core.py
--------------

ブラックリスト・正規表現・述語関数で
ノード一覧をフィルタリングするユーティリティ。
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, List, Pattern, Set


class FilterError(ValueError):
    """rvh_filter が投げる例外"""


def _compile(patterns: Iterable[str] | None) -> List[Pattern]:
    if not patterns:
        return []
    try:
        return [re.compile(p) for p in patterns]
    except re.error as exc:  # pragma: no cover
        raise FilterError(f"Invalid regex pattern: {exc}") from exc


def filter_nodes(
    nodes: Iterable[str],
    *,
    blacklist: Set[str] | None = None,
    regex_deny: Iterable[str] | None = None,
    predicate: Callable[[str], bool] | None = None,
) -> List[str]:
    """
    ノード ID リストから「除外条件に該当しない」ノードを返す。

    Parameters
    ----------
    nodes:
        対象ノード ID のイテラブル
    blacklist:
        完全一致で拒否するノード ID 集合
    regex_deny:
        正規表現で拒否するパターン群 (文字列の iterable)
    predicate:
        ``lambda node: bool`` な任意の述語関数  
        True を返すノードは **除外** される

    Returns
    -------
    list[str]
        フィルタ後のノード ID 一覧
    """
    bl = blacklist or set()
    regexes = _compile(regex_deny)
    deny_fn = predicate or (lambda _n: False)

    kept: list[str] = []
    for n in nodes:
        if n in bl:
            continue
        if any(r.search(n) for r in regexes):
            continue
        if deny_fn(n):
            continue
        kept.append(n)
    return kept


class NodeFilter:
    """
    OO ラッパ – 条件を持ち回れる。
    """

    def __init__(
        self,
        *,
        blacklist: Set[str] | None = None,
        regex_deny: Iterable[str] | None = None,
        predicate: Callable[[str], bool] | None = None,
    ) -> None:
        self._bl = blacklist or set()
        self._re = _compile(regex_deny)
        self._pred = predicate or (lambda _n: False)

    def __call__(self, nodes: Iterable[str]) -> List[str]:
        return filter_nodes(
            nodes,
            blacklist=self._bl,
            regex_deny=[r.pattern for r in self._re],
            predicate=self._pred,
        )
