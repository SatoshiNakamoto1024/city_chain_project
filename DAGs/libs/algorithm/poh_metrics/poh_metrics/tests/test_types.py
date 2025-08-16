# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_types.py
import pytest
from typing import get_args
from poh_metrics.types import PoHResult, GCType

def test_pohresult_literals():
    args = get_args(PoHResult)
    assert set(args) == {"success", "failure", "timeout"}

def test_gctype_literals():
    args = get_args(GCType)
    assert set(args) == {"minor", "major"}
