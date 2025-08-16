# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\test_filter.py

from rvh_filter import filter_nodes, NodeFilter, FilterError


def test_blacklist():
    nodes = ["n1", "bad", "n2"]
    assert filter_nodes(nodes, blacklist={"bad"}) == ["n1", "n2"]


def test_regex():
    nodes = ["edge-1", "edge-2", "val-1"]
    out = filter_nodes(nodes, regex_deny=[r"edge-\d"])
    assert out == ["val-1"]


def test_predicate():
    f = NodeFilter(predicate=lambda n: n.endswith("-x"))
    assert f(["a-x", "b", "c-x"]) == ["b"]


def test_error_regex():
    try:
        filter_nodes(["a"], regex_deny=["["])  # 不正な正規表現
    except FilterError:
        pass
    else:
        raise AssertionError("FilterError expected")
