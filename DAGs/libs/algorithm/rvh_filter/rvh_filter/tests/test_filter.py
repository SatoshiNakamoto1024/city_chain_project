# D:\city_chain_project\DAGs\libs\algorithm\rvh_filter\test_filter.py
import pytest

from rvh_filter import (
    filter_nodes,
    filter_nodes_async,
    NodeFilter,
    AsyncNodeFilter,
    FilterError,
)

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
    with pytest.raises(FilterError):
        filter_nodes(["a"], regex_deny=["["])  # Invalid regex

@pytest.mark.asyncio
async def test_async_blacklist():
    nodes = ["x", "y", "bad", "z"]
    out = await filter_nodes_async(nodes, blacklist={"bad"})
    assert out == ["x", "y", "z"]

@pytest.mark.asyncio
async def test_async_regex_and_predicate():
    nodes = ["aa", "bb", "cc1", "dd2"]
    af = AsyncNodeFilter(predicate=lambda n: n.endswith("2"), regex_deny=[r"cc\d"])
    out = await af(nodes)
    assert out == ["aa", "bb"]

@pytest.mark.asyncio
async def test_async_error_regex():
    with pytest.raises(FilterError):
        await filter_nodes_async(["a"], regex_deny=["["])
