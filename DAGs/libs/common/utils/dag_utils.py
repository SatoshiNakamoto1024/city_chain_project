# network/DAGs/common/utils/dag_utils.py
"""
DAG（有向非巡回グラフ）向けユーティリティ
=========================================
- トポロジカルソート  
- サイクル検出  
- エッジリスト→隣接リスト変換
"""

from __future__ import annotations
from collections import deque
from typing import Dict, List, TypeVar, Iterable

T = TypeVar("T")


def topological_sort(dependencies: Dict[T, List[T]]) -> List[T]:
    """
    トポロジカルソートを行う。

    Args:
        dependencies: ノードをキー、そこから出るエッジ先リストを値とした辞書

    Returns:
        ソート済みノードのリスト

    Raises:
        ValueError: サイクルが検出された場合
    """
    # 全ノードの in-degree を計算
    in_degree: Dict[T, int] = {node: 0 for node in dependencies}
    for succs in dependencies.values():
        for v in succs:
            in_degree[v] = in_degree.get(v, 0) + 1

    # in-degree=0 のノードから開始
    queue = deque(node for node, deg in in_degree.items() if deg == 0)
    result: List[T] = []

    while queue:
        u = queue.popleft()
        result.append(u)
        for v in dependencies.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(result) != len(in_degree):
        raise ValueError("Cycle detected in DAG")
    return result


def detect_cycle(dependencies: Dict[T, List[T]]) -> bool:
    """
    DFS を使ってグラフにサイクルがあるか判定する。

    Returns:
        True: サイクルあり
        False: サイクルなし
    """
    visited: set[T] = set()
    stack: set[T] = set()

    def dfs(u: T) -> bool:
        visited.add(u)
        stack.add(u)
        for v in dependencies.get(u, []):
            if v not in visited:
                if dfs(v):
                    return True
            elif v in stack:
                return True
        stack.remove(u)
        return False

    for node in dependencies:
        if node not in visited and dfs(node):
            return True
    return False


def flatten_edges(edges: Iterable[tuple[T, T]]) -> Dict[T, List[T]]:
    """
    エッジリスト (src, dst) のタプル列を隣接リスト辞書に変換する。

    Args:
        edges: (ソース, 宛先) のイテラブル

    Returns:
        ノード -> 後続ノードリスト の辞書
    """
    graph: Dict[T, List[T]] = {}
    for src, dst in edges:
        graph.setdefault(src, []).append(dst)
        # 存在だけは保証しておく
        graph.setdefault(dst, graph.get(dst, []))
    return graph
