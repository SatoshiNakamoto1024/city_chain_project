# infra/logging_setup.py
"""
アプリ全体で呼び出すだけで CloudWatch 送信が有効になる共通設定モジュール
"""
from __future__ import annotations
import os, logging, datetime
import watchtower                       # pip install watchtower

# ─────────────────────────────────────────────
#  設定値（環境変数で上書き可）
# ─────────────────────────────────────────────
LOG_GROUP  = os.getenv("CW_LOG_GROUP",  "/myapp/production")
# 日単位でログストリームを切る
_stream_nm = os.getenv("CW_LOG_STREAM",
                       f"{datetime.date.today():%Y%m%d}_backend")

LOG_LEVEL  = os.getenv("LOG_LEVEL", "INFO").upper()

def configure_logging() -> None:
    """
    何度呼んでも二重登録されない安全設計
    """
    root = logging.getLogger()
    if any(isinstance(h, watchtower.CloudWatchLogHandler) for h in root.handlers):
        return  # すでに設定済み

    # ---- CloudWatch ----
    cw_handler = watchtower.CloudWatchLogHandler(
        log_group       = LOG_GROUP,
        stream_name     = _stream_nm,
        use_queues      = True,       # 非同期
        send_interval   = 5,
    )
    cw_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s"
        )
    )

    # ---- Console (開発用) ----
    cons_handler = logging.StreamHandler()
    cons_handler.setFormatter(cw_handler.formatter)

    # ---- root へ適用 ----
    root.setLevel(LOG_LEVEL)
    root.addHandler(cons_handler)
    root.addHandler(cw_handler)

    # noisy な boto3 を少し下げる
    logging.getLogger("botocore").setLevel("WARNING")
    logging.getLogger("boto3").setLevel("WARNING")
