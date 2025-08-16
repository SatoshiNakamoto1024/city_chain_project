login/
  └── municipality_verification/
       ├── municipality_login.py        (職員ログイン用の Flask Blueprint)
       ├── municipality_verification.py       (ユーザー承認／却下の DynamoDB 操作)
       ├── municipality_views.py              (承認画面を表示＆フォーム受け取り)
       └── municipality_tools/          (職員向けツールの小分けフォルダ)
           ├── municipality_approval_logger.py   (承認／却下のログを DynamoDB へ記録)
           ├── municipality_jwt_utils.py         (JWT 検証用のユーティリティ)
           └── municipaliry_register_admin.py    (職員アカウントを登録するスクリプト)

# 5. admin_tools/approval_logger.py
役割
ユーザー承認／却下アクションの監査ログを、別テーブル (MunicipalApprovalLogTable) に保存する関数。
承認／却下した管理者ID (approver_id)、理由、実行時刻などをまとめて保存し、運用上の監査証跡を残す。

なぜ分けているか？
承認実行ロジック (verification.py) とログ記録 (approval_logger.py) を分割することで、コードが散らばるのを防ぎ、
将来、ログを別システム（S3 や外部監査APIなど）に送る際にも、このモジュールだけを修正すればよいようにしてあると推測される。

# 6. admin_tools/jwt_utils.py
役割
admin_login.py で生成した JWT をサーバー側で検証し、トークンが正しい＆有効期限内かを確かめる機能を提供するユーティリティ。不正・期限切れのトークンなら None を返して弾く。

なぜ分けているか？
JWT 検証は市町村職員用アクション全体で使い回される可能性が高いため、一箇所にまとめるメリットが大きい。
どのファイルからでも簡単にインポートできる。

#　7. admin_tools/register_admin.py
役割
コマンドラインから呼び出し可能なスクリプトで、新しい市町村職員アカウント（admin_id, password, name, municipality）を DynamoDB (MunicipalAdmins) に登録する。
ソルトを生成し、ソルト付きパスワードハッシュを作り、テーブルに保存。

ポイント
一般的に管理者アカウントを手動で登録・メンテナンスする必要があるので、専用スクリプト化している。
たとえば本番環境なら、DevOps担当がこのスクリプトを走らせて新規職員アカウントを発行するといったフローが想定できる。

#　全体の流れ（運用イメージ）
・管理者登録（ローカルで python register_admin.py を実行）
DynamoDB の MunicipalAdmins テーブルに職員アカウントが作成される。

・管理者がログイン（/admin_login ページ）
admin_id & password で認証→JWT 受け取り。

・ユーザー承認画面（/municipality_verify）
管理者が発行された JWT を持ってアクセスする。
承認待ちユーザー一覧（approval_status="pending") を見て、承認 or 却下を選択。
成功時に approval_logger.py でログが別テーブルに保存される。

・承認されたユーザー
これ以降 approval_status="approved" となり、正式にサービスを利用可能になる。

こうしたフローが、一連のファイルを通じて構成されています。


# test_admin_tools.pyのポイント
setup_test_tables フィクスチャでテスト用テーブルを作成・削除
ADMIN_TABLE と APPROVAL_LOG_TABLE のみ。
ユニットテストなので、本来は最小限のテストで OK。
test_register_admin → 実際に DynamoDB に管理者アカウントが登録されるか検証
test_log_approval → 実際に承認ログが書き込まれるか検証
test_generate_salt_and_hash は DynamoDB 関係なく純粋に関数の動作チェック
test_verify_admin_jwt_* は JWT の有効期限チェックなどを行う


動作確認
python municipality_registration/app_municipality_registration.py で /api/jis/ が動いていること
python municipality_verification/app_municipality_verification.py を起動
ブラウザで http://localhost:5000/admin_login

大陸→国→都道府県→市町村を選択 → ID/PW を入力 → ログイン
成功後 /municipality_verify へリダイレクトし、承認画面が表示される
これで 動的自治体選択＋職員認証フロー が一通り動くはずです。