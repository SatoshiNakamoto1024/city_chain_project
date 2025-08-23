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

from .exceptions import *          # noqa: F403
from .handlers import handle       # エントリポイント
from .policies import get_policy
from .logger import err_logger

__all__ = [
    "err_logger",
    # サブモジュール公開
    "exceptions",
    "get_policy",
    # 主要 API
    "handle",
    "handlers",
    "policies",
]
