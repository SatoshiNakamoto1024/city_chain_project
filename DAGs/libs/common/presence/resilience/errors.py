# D:\city_chain_project\network\DAGs\common\presence\resilience\errors.py
"""
presence.resilience.errors
--------------------------
共通例外クラス
"""


class CircuitOpenError(RuntimeError):
    """サーキットブレーカーが OPEN のため呼び出し不可"""


class RateLimitExceeded(RuntimeError):
    """レートリミット超過"""
