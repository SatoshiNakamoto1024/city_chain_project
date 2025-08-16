# D:\city_chain_project\network\DAGs\common\errors\__init__.py
"""
common.errors  ― 組織共通エラー管理パッケージ
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
・独自例外クラス            … exceptions.py
・リトライ/フォールバック   … handlers.py
・エラーポリシー定義        … policies.py
・専用ロガー                … logger.py
"""
from __future__ import annotations

from .exceptions import *          # noqa: F401,F403
from .handlers import handle       # エントリポイント
from .policies import get_policy
from .logger import err_logger

__all__ = [
    # サブモジュール公開
    "exceptions",
    "handlers",
    "policies",
    # 主要 API
    "handle",
    "get_policy",
    "err_logger",
]
