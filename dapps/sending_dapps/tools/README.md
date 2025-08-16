#　insert_user_to_dynamodb.py　によるPEM作成
1回のみ、python insert_user_to_dynamodb.py で4つのファイルを生成。
そして、_fixtures/ へ4つのファイルを移動。

実行後の構成例
dapps/
 └─ sending_dapps/
      ├─ _fixtures/
      │    ├─ client.pem
      │    ├─ ntru_sk.b64
      │    ├─ dilithium_pub.b64
      │    └─ dilithium_sk.b64
      └─ tools/
           └─ generate_client_fixture.py
           └─ insert_user_to_dynamodb.py
もし tools/_fixtures/ が既に出来てしまった場合は
rm -r sending_dapps/tools/_fixtures（またはエクスプローラで削除）
してから再実行してください。


✅ CWD に依存しないよう “スクリプト自身の場所” から辿る
以下が 修正版の全文。
generate_client_fixture.py と同じく file ベース で
_fixtures を探すので、どこで実行しても失敗しません。

使い方　① すでに dapps/sending_dapps/tools に居るなら
#  ↓　UUID を付ける
python insert_user_to_dynamodb.py fixture_user_b3428ca1　と実行する。
fixture_user_b3428ca1 は generate_client_fixture.py 実行時に表示された UUID を指定

_fixtures が正しい場所にない場合はエラーで止まります


# DynamoDB への投入が完了
生成スクリプトの末尾に表示される uuid を控え、
前回の insert_user_to_dynamodb.py で UsersTable に登録してください
（FIX のパスは変更不要 ― _fixtures 位置は同じなので）。

これで
鍵ペアと PEM が 1 ユーザーに完全対応
出力フォルダも sending_dapps/_fixtures に統一
となります。