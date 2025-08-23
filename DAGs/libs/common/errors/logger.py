# D:\city_chain_project\network\DAGs\common\errors\logger.py
"""
logger.py  ― エラー専用ロガー
JSON 形式で stdout に流すだけ。実運用で好みの logger に置き換えても OK。
"""
from __future__ import annotations
import json
import logging
import sys
from datetime import datetime
from typing import Any, Mapping

_LOGGER_NAME = "city_chain.errors"


def _json_formatter(record: logging.LogRecord) -> str:
    data: Mapping[str, Any] = {
        "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "lvl": record.levelname,
        "msg": record.getMessage(),
        "exc": record.exc_text,
        "module": record.module,
    }
    return json.dumps(data, ensure_ascii=False)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt=None))
_root = logging.getLogger(_LOGGER_NAME)
_root.setLevel(logging.INFO)
_root.addHandler(_handler)
_root.propagate = False  # 二重出力防止


def err_logger() -> logging.Logger:
    """呼び出し側用ファクトリ"""
    return _root


def log_exception(exc: Exception, extra_msg: str | None = None) -> None:
    """シンプルなログラッパー"""
    msg = extra_msg or str(exc)
    _root.error(msg, exc_info=exc)
