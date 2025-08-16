# 補足
本番実装用の強化点
・各入力項目のバリデーション（空文字、形式チェックなど）を強化
・JWT やパスワードハッシュはセキュアなライブラリを利用し、秘密鍵・ソルトの管理も厳格に
・AWS S3、DynamoDB との連携は本番用の IAM 権限・暗号化設定を利用
・エラーハンドリング、ロギングは詳細に実装し、運用監視も行う

crypto フォルダー
各暗号化モジュールはダミー実装ですが、実際には本物のライブラリ（例えば PyCryptodome、pqcrypto など）を利用してください。

テストコード
moto ライブラリを利用して AWS S3、DynamoDB をモックし、登録フローおよび生命体管理のフローをテストしています。
テストコード内では、AWS S3 や DynamoDB への接続は実際の AWS 環境ではなく、moto というモックライブラリを使用してエミュレートしています。
つまり、テスト実行時には実際の AWS サービスを起動・登録する必要はなく、moto がダミーの環境を提供してくれるため、ローカルで安全にテストが可能です。

これらのファイル群をプロジェクトに配置することで、初期登録から本人確認、ユーザー登録完了および生命体管理の処理が一通り動作することを検証できます。
必要に応じて各処理（入力検証、暗号処理、DB連携等）の詳細を強化してください。

# app_login.pyを実行結果
PS D:\city_chain_project\login\login_app> python app_login.py
 * Serving Flask app 'app_login'
 * Debug mode: on
[INFO] 2025-03-17 05:51:59,264 - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
[INFO] 2025-03-17 05:51:59,265 - Press CTRL+C to quit
[INFO] 2025-03-17 05:51:59,288 -  * Restarting with stat
[WARNING] 2025-03-17 05:52:00,488 -  * Debugger is active!
[INFO] 2025-03-17 05:52:00,497 -  * Debugger PIN: 927-675-991

よかったです！
このログは、Flask 開発サーバーが正常に起動している状態を示しています。
http://127.0.0.1:5000 にアクセスして動作確認してください。

もし今後本番環境に移行する場合は、WSGI サーバー（Gunicorn、uWSGI など）を使ってデプロイするようにしてください。