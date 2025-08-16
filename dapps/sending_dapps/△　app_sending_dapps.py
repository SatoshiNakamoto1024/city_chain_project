# dapps\sending_dapps\app_sending_dapps.py
"""
app_sending_dapps.py

このモジュールは、送信DApps のエントリーポイントです。
ユーザーからの入力（例：JSON ファイル経由や標準入力など）を受け取り、
トランザクションの整形・生成および整合性検証を行い、
最終的に生成されたトランザクションデータを標準出力に出力します。

※ 本番実装用として、固定のデータ（CityA, CityB など）を廃し、
  引数や標準入力から動的にデータを取得するように変更しました。
"""

import sys
import os
import json
import logging

# ── 重要 ──
# 本ファイルは dapps/sending_dapps/app_sending_dapps.py に配置される想定です。
# そのため、ルートを「プロジェクト直下」として sys.path に通す必要があります。
# 以下の sys.path.insert() を必ず上のほうに置いてください。

# プロジェクトルートにパスを通しておく
#   └ dapps/ の一つ上（プロジェクトルート）を追加
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from dapps.sending_dapps.transaction import prepare_transaction
from dapps.sending_dapps.validator import validate_transaction

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    使い方 (例):

      1) JSON ファイルを用意して渡す場合:
         > python app_sending_dapps.py input_data.json

      2) 標準入力から直接 JSON を渡す場合:
         > cat input_data.json | python app_sending_dapps.py

    input_data.json の例:
    {
      "sender": "Alice",
      "receiver": "Bob",
      "sender_wallet": "alice_wallet_address",
      "receiver_wallet": "bob_wallet_address",
      "amount": "123.45",
      "message": "Hello, Bob! Here's the payment.",
      "verifiable_credential": "credential_example",
      "subject": "Payment",
      "action_level": "high",
      "dimension": "global",
      "fluctuation": "none",
      "organism_name": "TestOrg",
      "sender_municipality": "Asia/Tokyo/Chiyoda/千代田区",   # 例: "大陸/都道府県/市町村"
      "receiver_municipality": "Asia/Tokyo/Shinjuku/新宿区",
      "receiver_uuid": "受信者ユーザーのUUID文字列",
      "details": "Payment for services",
      "goods_or_money": "money",
      "location": "Tokyo",
      "proof_of_place": "GPS_data",
      "account_title": "sales",
      "attributes": {"priority": "urgent"}
    }
    """
    input_json = None

    # コマンドライン引数でファイル名が渡された場合
    if len(sys.argv) >= 2:
        path = sys.argv[1]
        try:
            with open(path, "r", encoding="utf-8") as f:
                input_json = json.load(f)
        except Exception as e:
            logger.error("入力ファイルの読み込みに失敗: %s", e)
            sys.exit(1)
    else:
        # 標準入力から読み込む
        try:
            raw = sys.stdin.read()
            input_json = json.loads(raw)
        except Exception as e:
            logger.error("標準入力からの JSON 読み込みに失敗: %s", e)
            sys.exit(1)

    # トランザクション整形
    try:
        transaction = prepare_transaction(input_json)
        print("=== 整形されたトランザクション ===")
        print(json.dumps(transaction, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("トランザクション整形に失敗: %s", e)
        sys.exit(1)

    # バリデーション
    try:
        is_valid = validate_transaction(transaction)
        if is_valid:
            print("[Validator] トランザクションの整合性検証に成功しました。")
        else:
            print("[Validator] トランザクションの整合性検証に失敗しました。")
    except Exception as e:
        logger.error("バリデーション実行時にエラー: %s", e)
        sys.exit(1)

    # ここで生成されたトランザクションは、後続のDAGモジュールへ引き渡すことを想定
    # たとえば、ファイルに保存する、別サービスに送信する、などの処理をここに追加できます。


if __name__ == "__main__":
    main()
