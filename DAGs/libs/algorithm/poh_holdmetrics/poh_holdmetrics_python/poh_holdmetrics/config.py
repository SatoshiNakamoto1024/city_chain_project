# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\config.py
# -*- coding: utf-8 -*-
"""
poh_holdmetrics ― アプリケーション設定

* .env  または OS 環境変数から読み込む
* すべてデフォルト値付きなので、未設定でもローカル環境で起動可能
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------------------------------------------------------------------
    # ネットワーク / サーバ
    # ---------------------------------------------------------------------
    grpc_address: str = Field(
        "0.0.0.0:60051",
        alias="GRPC_ADDRESS",
        description="gRPC サーバ待ち受けアドレス",
    )
    http_host: str = Field(
        "0.0.0.0",
        alias="HTTP_HOST",
        description="HTTP サーバ bind ホスト",
    )
    http_port: int = Field(
        8000,
        alias="HTTP_PORT",
        description="HTTP サーバ port",
    )
    log_level: str = Field(
        "INFO",
        alias="LOG_LEVEL",
        description="ログレベル（DEBUG / INFO / WARNING / ERROR）",
    )

    # ---------------------------------------------------------------------
    # メトリクス収集間隔など
    # ---------------------------------------------------------------------
    collect_interval: int = Field(
        10,
        alias="COLLECT_INTERVAL",
        description="snapshot を外部へ送信する秒間隔",
    )
    gc_interval: int = Field(
        600,
        alias="GC_INTERVAL",
        description="内部 GC（イベント整理）を行う秒間隔",
    )

    # ---------------------------------------------------------------------
    # MongoDB 接続設定
    #   * 未設定ならローカル `mongodb://localhost:27017`
    #   * DB 名が未設定なら `holdmetrics`
    # ---------------------------------------------------------------------
    mongodb_url: str | None = Field(
        default=None,
        alias="MONGODB_URL",
        description=(
            "MongoDB URI  (例: "
            "mongodb+srv://user:pass@cluster0.example.mongodb.net/"
            "?retryWrites=true&w=majority)"
        ),
    )
    mongodb_db: str | None = Field(
        default=None,
        alias="MONGODB_DB",
        description="MongoDB データベース名（例: holdmetrics）",
    )

    # ---------------------------------------------------------------------
    # 共通モデル設定
    # ---------------------------------------------------------------------
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,   # 環境変数名の大文字小文字を無視
    )

    # --- Exporters ---
    otlp_endpoint: str = Field(
        "localhost:4317",
        alias="OTLP_ENDPOINT",
        description="OTLP gRPC endpoint (host:port)",
    )
    prometheus_port: int = Field(
        8001,
        alias="PROMETHEUS_PORT",
        description="Prometheus /metrics ポート",
    )

# ------------------------------------------------------------
# シングルトン
# ------------------------------------------------------------
settings = Settings()
