# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\tests\test_faultset.py
import pytest
from rvh_faultset import faultset, faultset_async, FaultsetError

NODES = [
    {"id": "a", "lat": 35.0, "lon": 139.0, "latency":  50.0},
    {"id": "b", "lat": 51.5, "lon":   -0.1, "latency": 200.0},
    {"id": "c", "lat": 40.7, "lon":  -74.0, "latency":  75.0},
]

def test_basic_faultset():
    sel = faultset(NODES, threshold=100.0, precision=5)
    assert isinstance(sel, list)
    assert set(sel) == {"a", "c"}

def test_empty_nodes():
    with pytest.raises(FaultsetError):
        faultset([], threshold=50.0)

def test_cluster_empty():
    with pytest.raises(FaultsetError):
        faultset(NODES, 10.0, precision=12)

@pytest.mark.asyncio
async def test_basic_faultset_async():
    sel = await faultset_async(NODES, threshold=100.0, precision=5)
    assert isinstance(sel, list)
    assert set(sel) == {"a", "c"}

@pytest.mark.asyncio
async def test_empty_nodes_async():
    with pytest.raises(FaultsetError):
        await faultset_async([], threshold=50.0)
