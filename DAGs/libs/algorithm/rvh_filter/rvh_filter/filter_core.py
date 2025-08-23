# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\filter_core.py
"""
filter_core.py
--------------

ブラックリスト・正規表現・述語関数で
ノード一覧をフィルタリングするユーティリティ。
"""
from __future__ import annotations

import re
import asyncio
from typing import Callable, Iterable, List, Pattern, Set, TypeVar, Optional

T = TypeVar("T")  # for generic predicate


class FilterError(ValueError):
    """rvh_filter が投げる例外"""


def _compile(patterns: Optional[Iterable[str]]) -> List[Pattern]:
    if not patterns:
        return []
    try:
        return [re.compile(p) for p in patterns]
    except re.error as exc:  # pragma: no cover
        raise FilterError(f"Invalid regex pattern: {exc}") from exc


def filter_nodes(
    nodes: Iterable[str],
    *,
    blacklist: Optional[Set[str]] = None,
    regex_deny: Optional[Iterable[str]] = None,
    predicate: Optional[Callable[[str], bool]] = None,
) -> List[str]:
    """
    同期版：ノード ID リストから除外条件を満たさないものを返す。
    """
    bl = blacklist or set()
    regexes = _compile(regex_deny)
    deny_fn = predicate or (lambda _: False)

    kept: List[str] = []
    for n in nodes:
        if n in bl:
            continue
        if any(r.search(n) for r in regexes):
            continue
        if deny_fn(n):
            continue
        kept.append(n)
    return kept


async def filter_nodes_async(
    nodes: Iterable[str],
    *,
    blacklist: Optional[Set[str]] = None,
    regex_deny: Optional[Iterable[str]] = None,
    predicate: Optional[Callable[[str], bool]] = None,
) -> List[str]:
    """
    非同期版：内部でスレッドプールを使い同期 filter_nodes を実行します。
    """
    return await asyncio.to_thread(
        filter_nodes,
        nodes,
        blacklist=blacklist,
        regex_deny=regex_deny,
        predicate=predicate,
    )


class NodeFilter:
    """
    同期版 OO ラッパー。
    """
    def __init__(
        self,
        *,
        blacklist: Optional[Set[str]] = None,
        regex_deny: Optional[Iterable[str]] = None,
        predicate: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self._bl = blacklist or set()
        self._re = _compile(regex_deny)
        self._pred = predicate or (lambda _: False)

    def __call__(self, nodes: Iterable[str]) -> List[str]:
        return filter_nodes(
            nodes,
            blacklist=self._bl,
            regex_deny=[r.pattern for r in self._re],
            predicate=self._pred,
        )


class AsyncNodeFilter:
    """
    非同期版 OO ラッパー。
    """
    def __init__(
        self,
        *,
        blacklist: Optional[Set[str]] = None,
        regex_deny: Optional[Iterable[str]] = None,
        predicate: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self._bl = blacklist or set()
        self._re = _compile(regex_deny)
        self._pred = predicate or (lambda _: False)

    async def __call__(self, nodes: Iterable[str]) -> List[str]:
        return await filter_nodes_async(
            nodes,
            blacklist=self._bl,
            regex_deny=[r.pattern for r in self._re],
            predicate=self._pred,
        )
