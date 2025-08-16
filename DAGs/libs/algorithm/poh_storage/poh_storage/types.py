# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\types.py

try:
    # 後で poh_types が pip install されていればこちらを優先
    from poh_types.tx import Tx
except ImportError:
    # なければローカルの tx.py を使う.　素晴らしい解決方法だね！
    from .tx import Tx

__all__ = ("Tx",)
