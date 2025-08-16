# network/DAGs/common/utils/test_utils.py
import pytest
import base64
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.app_utils import app


@pytest.mark.asyncio
async def test_tx_types_endpoints():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as cli:
            # list
            r = await cli.get("/tx_types")
            assert r.status_code == 200
            vals = r.json()["values"]
            assert "TRANSFER" in vals and "VOTE" in vals

            # valid
            r2 = await cli.get("/tx_types/validate", params={"value": "TRANSFER"})
            assert r2.status_code == 200 and r2.json() == {"valid": True}

            # invalid
            r3 = await cli.get("/tx_types/validate", params={"value": "FOO"})
            assert r3.status_code == 200 and r3.json() == {"valid": False}


@pytest.mark.asyncio
async def test_dag_utils_endpoints():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as cli:
            edges = [["A", "B"], ["A", "C"], ["B", "D"]]

            # sort
            r = await cli.post("/dag/sort", json={"edges": edges})
            assert r.status_code == 200
            order = r.json()["order"]
            assert order.index("A") < order.index("B") < order.index("D")

            # detect_cycle: no
            r2 = await cli.post("/dag/detect_cycle", json={"edges": edges})
            assert r2.status_code == 200 and r2.json()["cycle"] is False

            # detect_cycle: yes
            cyc = [["X", "Y"], ["Y", "X"]]
            r3 = await cli.post("/dag/detect_cycle", json={"edges": cyc})
            assert r3.status_code == 200 and r3.json()["cycle"] is True

            # flatten
            r4 = await cli.post("/dag/flatten", json={"edges": edges})
            assert r4.status_code == 200
            graph = r4.json()["graph"]
            assert graph["A"] == ["B", "C"]
            assert "D" in graph


@pytest.mark.asyncio
async def test_constants_and_errors_endpoints():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as cli:
            # constants
            r = await cli.get("/constants")
            data = r.json()
            assert "MAX_DAG_NODES" in data and isinstance(data["MAX_DAG_NODES"], int)
            assert data["SHARD_SIZE_LIMIT"] == 100 * 1024 * 1024

            # DAGCycleError
            r2 = await cli.get("/errors/dag_cycle")
            assert r2.status_code == 400
            assert r2.json()["detail"] == "Cycle detected"

            # InvalidTxTypeError
            r3 = await cli.get("/errors/invalid_tx")
            assert r3.status_code == 422
            assert r3.json()["detail"] == "Invalid TxType"
