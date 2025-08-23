from typing import List, Dict


def count_nodes(dag: Dict[str, List[str]]) -> int:
    """
    DAGを {node: [children,...], ...} の形式で受け取り、
    ユニークなノード数を返す。
    """
    nodes = set(dag.keys())
    for children in dag.values():
        nodes.update(children)
    return len(nodes)


def depth_statistics(dag: Dict[str, List[str]]) -> Dict[str, float]:
    """
    DAGの最大深度・平均深度を計算する（再帰／DP）。
    """
    memo = {}

    def depth(u):
        if u in memo:
            return memo[u]
        ds = [depth(v) for v in dag.get(u, [])]
        d = 1 + (max(ds) if ds else 0)
        memo[u] = d
        return d

    depths = [depth(u) for u in nodes]
    return {
      "max_depth": max(depths),
      "avg_depth": sum(depths) / len(depths) if depths else 0.0
    }
