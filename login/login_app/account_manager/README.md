# staff,adminの両方を加えたい。
DBも,MunicipalStaffs（PK:municipality_id (s), ソートキー：municipality (s)）, 
AdminsTable（PK:admin_id (s),ソートキー：session_id (s)）, 
にて上記のようにコードを二重に書く必要はない。
「role」という 1 フィールドで 共通登録・共通ログインを切り替える。

新規に書くのは職員専用フロントと承認 API だけ。
既存の auth_py・crypto・device_manager は一切コピーしなくていい。というのでやってみたい。どのファイルをどう修正したらいい？実装用になるように、省略せずに記載して貰えますか。

ChatGPT said:
下記の 新規 6 ファイル だけ追加／差し替えれば住民・市町村職員（staff）・システム管理者（admin） を
1 本の共通ロジックで登録／ログインできる

職員データは MunicipalStaffs、
管理者データは AdminsTable に自動で振り分け

フロントは /staff/register, /staff/login, /admin/register, /admin/login という薄いエンドポイントを呼ぶだけ
になります。既存の巨大な registration/registration.py や auth_py/*, crypto/* は 一切触りません。

# account_manager/test_account_manager.py
"""
account_manager だけを検証する本番 DynamoDB 用テスト
--------------------------------------------------
* 登録 → サマリ行存在 → login 成功 だけを見る
* registration.register_user は monkeypatch で超軽量スタブ
* 本番テーブルに書き込み → テスト末尾でクリーンアップ
"""