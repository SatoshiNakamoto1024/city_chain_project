# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\builder.py
# poh_request/builder.py
"""Build, sign and Base58‑encode PoH_REQUEST transactions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from nacl import signing
from nacl.encoding import RawEncoder

from .exceptions import EncodeError
from .schema import PoHRequest
from .utils import b58encode, generate_nonce


class PoHRequestBuilder:
    """
    Helper to construct, sign and encode PoH_REQUEST payloads.
    """

    # ------------------------------------------------------------------ #
    # ctor
    # ------------------------------------------------------------------ #
    def __init__(
        self,
        private_key: signing.SigningKey,
        *,
        token_id: str,
        holder_id: str,
        amount: int,
        nonce: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self._sk = private_key
        self._req = PoHRequest(
            token_id=token_id,
            holder_id=holder_id,
            amount=amount,
            nonce=nonce or generate_nonce(),
            created_at=created_at or datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #
    def _canonical_json(self, *, exclude_sig: bool = False) -> bytes:
        """
        Return canonical (whitespace‑free) JSON bytes.
        `exclude_sig=True` で `signature` フィールドを除外。
        Pydantic の `mode="json"` で datetime → ISO‑8601 へ変換。
        """
        data = self._req.model_dump(exclude={"signature"} if exclude_sig else None)
        return json.dumps(data, separators=(",", ":")).encode()

    def _digest(self) -> bytes:
        """SHA‑256( canonical JSON without signature )."""
        return hashlib.sha256(self._canonical_json(exclude_sig=True)).digest()

    # ------------------------------------------------------------------ #
    # public api
    # ------------------------------------------------------------------ #
    @property
    def request(self) -> PoHRequest:  # read‑only
        return self._req

    # ---- signing ------------------------------------------------------ #
    def sign(self) -> "PoHRequestBuilder":
        """
        Ed25519 署名を計算して Base58 文字列として `signature` に格納。
        """
        try:
            sig_raw = self._sk.sign(self._digest(), encoder=RawEncoder).signature
            self._req.signature = b58encode(sig_raw)
            return self
        except Exception as exc:  # noqa: BLE001
            raise EncodeError(f"Failed to sign request: {exc}") from exc

    # ---- encoding ----------------------------------------------------- #
    def encode(self) -> str:
        """
        Base58‑encoded JSON を返す。未署名なら自動で `sign()`。
        """
        if self._req.signature is None:
            self.sign()
        return b58encode(self._canonical_json())
