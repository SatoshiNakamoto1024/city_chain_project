class IdempotencyError(Exception):
    """同一TxIDを重複処理しようとしたときに投げる例外"""
    pass
