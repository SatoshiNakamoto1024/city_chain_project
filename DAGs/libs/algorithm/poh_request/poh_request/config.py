# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\config.py
# poh_request/poh_request/config.py
"""Runtime configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings for PoH_REQUEST."""

    # RPC endpoint to which the Base58‑encoded payload is POSTed
    rpc_endpoint: str = Field(
        "https://api.poh-chain.example.com/tx",
        alias="POH_RPC_ENDPOINT",
        description="HTTP(S) URL for submitting PoH_REQUEST transactions",
    )

    # HTTP client settings
    request_timeout: float = Field(
        10.0,
        alias="POH_REQUEST_TIMEOUT",
        ge=1.0,
        description="Per‑request timeout in seconds",
    )
    retry_attempts: int = Field(
        3,
        alias="POH_RETRY_ATTEMPTS",
        ge=0,
        le=10,
        description="Number of retry attempts on failure",
    )
    backoff_base: float = Field(
        0.5,
        alias="POH_BACKOFF_BASE",
        ge=0.1,
        description="Base delay for exponential backoff",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

# singleton
settings = Settings()
