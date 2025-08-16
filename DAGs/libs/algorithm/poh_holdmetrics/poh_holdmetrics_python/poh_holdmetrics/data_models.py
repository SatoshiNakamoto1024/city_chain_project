# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\data_models.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HoldEvent(BaseModel):
    token_id: str
    holder_id: str
    start: datetime
    end: Optional[datetime] = None
    weight: float = 1.0

class HoldStat(BaseModel):
    holder_id: str
    weighted_score: float
