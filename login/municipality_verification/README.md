login_app/
├── app_login.py          ← Flaskアプリ起動 & Blueprint統合
├── config.py
└── municipality_verification/
    ├── __init__.py
    ├── views.py          ← municipality_verify_bp の中身（旧 municipality_verify.py）
    ├── verification.py   ← 登録された個人情報と照合するロジック（純粋関数）
    ├── admin_login.py    ← 管理者認証用JWTロジック
    └── admin_tools/
        └── approval_logger.py  ← CloudTrail風ログ機能

# 1. admin_login.py
市町村の職員(=管理者)がログインするためのエンドポイントを定義する Flask Blueprint。
DynamoDB（MunicipalAdmins テーブル）に保存されている管理者ID・パスワードハッシュをチェックし、正しければ JWT を生成して返す。これにより、管理者がシステム内の承認機能にアクセス可能となる。

✅ config.py のポイント
項目	用途
JWT_SECRET	JWT署名用の秘密鍵（本番では強力な値にして環境変数で）
APPROVAL_LOG_TABLE	承認ログの保存先（市町村職員の承認・却下）
ADMIN_TABLE	職員ログイン用のDynamoDBテーブル
LOGIN_HISTORY_TABLE	任意：ログイン履歴の保存に使えるテーブル名
PASSWORD_SALT_SIZE	パスワード暗号化時のソルト長さ
⇒　Flask アプリや各種 AWS リソース名、JWT の暗号情報などを一括管理する設定ファイル。
　　.env や環境変数から読み込む仕組みも取り入れられており、本番とローカルで設定を切り替えられるようにしている。

# 3. verification.py
主に市町村が承認を待っているユーザー（approval_status = pending）を一覧取得したり、承認(approved)・却下(rejected)に変更したりする DynamoDB 操作ロジックをまとめたファイル。
いわゆる「承認対象ユーザーの一覧取得／承認更新／却下更新」を担当。

# 4. views.py
市町村がユーザーを承認／却下するための画面表示 (municipality_verify.html) と、フォームPOSTを受け取る部分。
verification.py の approve_user／reject_user を呼び出して DynamoDB を更新し、
log_approval を呼んで承認ログを別テーブル (MunicipalApprovalLogTable) へ記録。
verify_admin_jwt を使って、管理者が正当なトークンを持っているかチェック（職員ログインの検証）をしている。

✅ TABLE構成（実用向け）
MunicipalAdmins テーブル（市町村職員ログイン用）の パーティションキー（PK）とソートキー（SK） は、
何を主軸に認証・識別するかに応じて設計します。
📌 テーブル名：MunicipalAdmins
キー種別	属性名	型	説明
パーティションキー	admin_id	String	職員ID（ログインに使用）例: komatsu001 など
ソートキー	municipality	String	市町村名（またはコード）例: Komatsu、Nomi

🔍 なぜこの構成？
admin_id はログインIDとして使える。
同じ admin_id を別の市町村が持つ可能性もあるため、municipality でスコープを明確にします。
「○○市の職員△△さん」として一意になる。

🧾 その他の属性（項目）
属性名	型	用途
password_hash	String	パスワードのハッシュ（平文では保存しない）
salt	String	パスワードハッシュに使うソルト
role	String	staff, supervisor など役職区分（任意）
email	String	メールアドレス（通知用途など）
created_at	String	登録日時
last_login_at	String	最終ログイン日時（ログイン時に更新）

✅ 登録例
{
  "admin_id": "komatsu001",
  "municipality": "Komatsu",
  "password_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
  "salt": "3f6d21a2...",
  "email": "staff001@komatsu.local",
  "role": "staff",
  "created_at": "2025-03-31T10:30:00Z",
  "last_login_at": "2025-04-01T09:45:00Z"
}

🔐 認証時の流れ
ログインフォームで admin_id, municipality, password を送信
DynamoDB の get_item で取得（admin_id + municipality）
ソルト付きハッシュでパスワード検証
成功すれば JWT 発行（admin_id を payload に含める）


✅ 本番用に必要な機能と拡張提案
① 登録内容と市町村保有データの自動照合機能
📌 説明：
市町村側には「住民台帳」や「My Number管理DB」があるという前提。
ユーザー登録内容（氏名、生年月日、住所、マイナンバー）を、既存の自治体データと自動突合する。

💡 実装方法：
登録された uuid をキーに DynamoDB から登録情報を取得。
事前にインポートした「正規データ（CSV/DB）」と照合。
すべて一致した場合のみ「自動承認」または「自動ハイライト」で目視確認しやすくする。

② 市町村の職員ログイン機能（職員認証）
📌 説明：
担当者ごとにログインを行い、どの職員が承認したかを記録。

💡 実装方法：
/admin_login エンドポイントを用意。
JWT または IP 制限でログイン管理。
各操作に「処理者名」「処理日時」を記録（ログテーブル or CloudTrail風ログ）

③ 承認ログの保存
📌 説明：
誰が・いつ・どの登録データに対して「承認」または「却下」したかを記録。

💡 実装方法：
MunicipalApprovalLogTable を用意（DynamoDB）。
uuid, approver_id, timestamp, action, reason, client_ip を保存。

④ 本人確認書類のアップロード機能（任意）
📌 説明：
ユーザーがマイナンバーカードや運転免許証の画像をアップロードし、それを市町村が確認する。

💡 実装方法：
S3バケットに保存 → 管理画面にサムネイル表示。
担当者は照合し、「画像確認済み」のチェックを入れる。

⑤ 自治体の正規データをインポートする仕組み
📌 説明：
CSV や Excel による自治体データ（氏名・生年月日・住所・マイナンバー）を取り込み、突合用DBとして保存。

💡 実装方法：
/admin/import_citizens のような管理者用APIでCSVを取り込み。
S3 または DynamoDB（CitizenMasterTable）に保存。
ユーザー登録時に自動で照合。

✅ 追加UI案（担当者向け）
✅ 照合画面に追加すべき項目：
登録内容	照合内容	一致?
氏名	登録内容 vs DB	○/×
生年月日	同上	○/×
マイナンバー	同上	○/×
住所	同上	○/×
書類アップロード	サムネイル	確認済みボタン
✅ 次にできること
✅ 市町村の正規データ用 CitizenMasterTable を追加し、CSVアップロード＆検索機能を作る

✅ 照合ロジックを verification.py に実装する（氏名、住所、マイナンバーなどで自動一致チェック）

✅ 承認ログ（ApprovalLogTable）を残すようにする

✅ 本人確認書類（画像）のアップロードとダウンロードを追加する

✅ 市町村職員ログイン機能を追加する（admin_login）


✅ 現在できていること（完了済み）
項目	状況
username / password / 証明書フィンガープリントによる認証	✅ 実装済み（auth.py）
JWT の発行と返却	✅ 済み
DynamoDB 読み込み & ハッシュ比較	✅ 正常動作
クライアント側（HTMLフォーム + JS）	✅ login.html 完成済み
/login Blueprint の定義と POST 処理	✅ 実装済み
SSO不要での DynamoDB 認証	✅ シンプル構成でOK

🔍 あと少しで完璧になる改善ポイント
① セッションへの JWT 保存・維持（今は未使用）
今の状態では、ログイン成功してもブラウザ側に jwt_token を保存していません。
改善例:
localStorage に jwt_token を保存
必要に応じて /profile や /lifeform に送信する際に Authorization: Bearer で送る
💡JWTをサーバーセッションに保存しないのは、フロントエンド中心のアーキテクチャでは推奨されます。

② ログイン後の自動リダイレクト
現在は alert() のみ。
成功時に /lifeform?uuid=... や /dashboard へリダイレクトすると UX 向上。
必要なら Flask セッション（session["uuid"] = ...）も併用。

③ JWT の署名強化（今後）
現在は HS256 + SECRET_KEY。
将来的には:
RS256 or ES256（公開鍵暗号方式）へ移行
JWT にクレーム追加（username, scope, exp, nbf, iat など）

④ client_cert_fp のチェックをもっと厳密に？
現在は文字列一致だけ。
本格運用では以下を考慮：
実際の証明書を読み込んでフィンガープリントを再生成
TLS証明書の検証（将来的に Flask + HTTPS 実装時に対応）

⑤ パスワード試行制限・ログ監視
不正アクセス対策（ブルートフォース防止）として：
連続ログイン失敗でブロック
SNSやCloudWatchログで管理者へ通知
CognitoやWAF導入でも代替可能

⑥ ログイン履歴保存（任意）
DynamoDB に LoginHistoryTable を作成し、ログイン成功ごとに記録：
uuid, timestamp, IP address, user_agent など

✅ まとめ：今すぐ必要な追加は？
優先度	項目
★★★	jwt_token を localStorage に保存（ログイン後の利用のため）
★★☆	ログイン成功後の自動リダイレクト
★★☆	JWT に username を含める（プロフィールやトランザクション時に使う）
★☆☆	ログイン履歴の記録 or ログ監視の導入
★☆☆	パスワード試行制限（ブルートフォース対策）
必要であれば：

login.html をリダイレクト付きに修正
JWTをlocalStorageに保存するJSを追加
/profile や /lifeform で jwt_token を受け取って認証する構成へ拡張できます。


#　test_municipality_verificationポイント
# staff_login.htmlからは
「staff001 / secret123」 というダミー認証情報を入力すれば、今のコード上では必ずログイン成功します。
（municipality フィールドは空ではないよう、ドロップダウンを１つ以上選んでください）

実際の DynamoDB 登録済みアカウント を使う場合は、register_municipality などで作成した staff_id とパスワードを使ってログインしてください。
以上を参考に、正しい staff_id / password を入力し直してみてください。

#　setup_test_tables_for_municipality
UsersTableTest を作成・削除（AdminTableTest や ApprovalLogTest は前のテストと共用している想定）
verification.py 内部で users_table = dynamodb.Table(DYNAMODB_TABLE) を使っているため、そのまま動作可能。

・test_full_verification_flow
管理者アカウントを register_admin で DynamoDB に登録 → そのアカウントでログインし JWT を取得
pending 状態のユーザーを追加
/municipality_verify/ に対して承認リクエストをPOST → 成功メッセージをHTMLから確認
DynamoDB の UsersTableTest で承認状態が approved に変わったか＆承認ログが残ったかをチェック。

====================================================== test session starts ======================================================
platform win32 -- Python 3.14.0a4, pytest-8.3.4, pluggy-1.5.0 -- D:\Python\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\login\login_app\municipality_verification
plugins: asyncio-0.25.3
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collected 1 item

test_municipality_verification.py::test_full_verification_flow PASSED     