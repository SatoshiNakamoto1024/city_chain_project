login/
 └ wallet/
      ├── __init__.py
      ├── config.py
      ├── wallet_model.py
      ├── wallet_db.py
      ├── wallet_service.py
      ├── wallet_routes.py
      └── app_wallet.py   ← 単体起動用（開発テスト）


 ステップ 1：JSON ファイルを作成
create_gsi.json という名前で保存します。

そして、
aws dynamodb update-table `
  --table-name WalletsTable `
  --attribute-definitions AttributeName=user_uuid,AttributeType=S `
  --global-secondary-index-updates file://create_gsi.json



この 1 ファイルを login/wallet/config.py に置けば、
from login.wallet.config import WALLET_TABLE, AWS_REGION, JWT_SECRET

のようにして どのモジュールからでも一貫した設定値 を取得できます。


# app_wallet.py だけでサーバーを立てたい場合
既にお渡しした最新版は
python login/wallet/app_wallet.py --serve           # デフォルト :5050
# または
python login/wallet/app_wallet.py --serve --port 6000
で Flask が起動します。
test_wallet.py は pytest がモックサーバーを作るので、
別途サーバーを立てる必要はありません。単に：
python -m pytest login/wallet/test_wallet.py

とすれば、DynamoDB が見つかる環境なら通るはずです。