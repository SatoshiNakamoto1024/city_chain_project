# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_calculator.py
import pytest
from poh_holdmetrics.calculator import calculate_score
from poh_holdmetrics.data_models import HoldEvent
from datetime import datetime, timedelta

def test_calculate_score_zero():
    now = datetime.utcnow()
    ev = HoldEvent(token_id="a", holder_id="h", start=now, end=now, weight=1.0)
    assert calculate_score([ev]) == 0.0

def test_calculate_score_multiple():
    now = datetime.utcnow()
    evs = [
        HoldEvent("a", "h1", now - timedelta(seconds=3), now, 1.0),
        HoldEvent("b", "h2", now - timedelta(seconds=2), now, 0.5),
    ]
    score = calculate_score(evs)
    # h1: 3*1 + h2: 2*0.5 = 3 + 1 = 4
    assert score == pytest.approx(4.0)
