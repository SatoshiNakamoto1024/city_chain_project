# network/DAGs/common/security/config.py
"""
config.py
──────────
– セキュリティ関連ユーティリティが参照する
  *環境変数名* を一元管理するだけの超軽量モジュール。
  値（パス）は **ここで決定しない** ことに注意してください。
"""

CLIENT_CERT_ENV = "CLIENT_CERT_PATH"
CLIENT_KEY_ENV  = "CLIENT_KEY_PATH"
CA_CERT_ENV     = "CA_CERT_PATH"
