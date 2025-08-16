# もし将来的にエラー定義が増えたら、ここに errors.py を追加するとよいでしょう。
# network/DAGs/common/utils/errors.py
"""
共通例外定義
"""
class AppError(Exception):
    """アプリケーション内で共通的に使う基本例外"""
    pass

class DAGCycleError(AppError):
    """DAG のサイクル検出時に投げる例外"""
    pass

class InvalidTxTypeError(AppError):
    """TxType 不正時に投げる例外"""
    pass
