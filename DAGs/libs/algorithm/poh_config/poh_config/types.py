# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\types.py
# poh_config/types.py
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class Config:
    MIN_POH_REQUIRED: int
    TTL_SECONDS: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        return cls(
            MIN_POH_REQUIRED=int(data["MIN_POH_REQUIRED"]),
            TTL_SECONDS=float(data["TTL_SECONDS"]),
        )
