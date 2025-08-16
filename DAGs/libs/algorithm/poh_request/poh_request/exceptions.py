# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\exceptons.py
"""Package‑wide custom exceptions."""


class PoHRequestError(Exception):
    """Base exception."""


class EncodeError(PoHRequestError):
    """Signing / encoding failed."""


class SendError(PoHRequestError):
    """HTTP send failed."""
