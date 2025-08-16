# D:\city_chain_project\network\DAGs\common\errors\exceptions.py
"""
exceptions.py  ― 共通例外クラス
"""
from __future__ import annotations
from dataclasses import dataclass


class BaseError(Exception):
    """すべての独自例外の親。"""

    retryable: bool = False       # デフォルト: リトライ不可
    alert: bool = True            # デフォルト: アラートを飛ばす


# ───────────────────────────
# カテゴリ別
# ───────────────────────────
class ValidationError(BaseError):
    """入力検証エラー (4xx 相当)"""

    retryable = False
    alert = False


class NetworkError(BaseError):
    """ネットワーク関連 (gRPC/TCP/HTTP)"""

    retryable = True


class StorageError(BaseError):
    """Mongo/Redis などストレージ系"""

    retryable = True


class SecurityError(BaseError):
    """署名検証・認可失敗など"""

    retryable = False
    alert = True


# ───────────────────────────
# 追加メタ情報を持つ例外
# ───────────────────────────
@dataclass(slots=True, frozen=True)
class DetailedError(BaseError):
    """外部 API 呼び出しなどで付帯情報を持たせたいときに使う"""

    code: str
    detail: str
