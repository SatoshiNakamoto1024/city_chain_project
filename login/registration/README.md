registration/
├── __init__.py
├── app_registration.py  # 登録に関するAPI集約
├── config.py
├── registration.py      # ユーザー登録ロジック
├── email_sender.py      # SNSメール送信、QR生成など

まとめ
これで「registration モジュール」に関するファイルを整理 & Blueprint化し、
registration.py : 登録ロジック
app_registration.py : Flaskルートの実装
email_sender.py : SNS通知やQRコード生成など
config.py : AWS_REGION, S3_BUCKETなど
と役割が完全に独立しました。
ご希望どおり「各ファイルの修正後の全文」を省略せず提示しているので、ぜひこのままコピペ or 参考にしてみてください。


このコードの意味は？
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

__file__
→ 今実行しているファイルのフルパス。ここでは test_auth_integration.py

os.path.dirname(__file__)
→ ファイルがあるディレクトリ（＝D:\city_chain_project\login\auth_py）

os.path.join(..., "..")
→ その1つ上のディレクトリ（＝D:\city_chain_project\login）

os.path.abspath(...)
→ 相対パスを絶対パスに直す（＝D:\city_chain_project\login）

sys.path.append(...)
→ Python がモジュールを探すパスに D:\city_chain_project\login を追加！

✅ これによって何ができる？
これによって registration/registration.py のように login と同じ階層にある別フォルダ のモジュールを以下のようにインポートできるようになります：
from registration.registration import register_user

🧭 図で整理すると
D:\city_chain_project\
│
├─ login\
│   ├─ auth_py\
│   │   └─ test_auth_integration.py ←ここから実行
│
├─ registration\
│   └─ registration.py ←これを使いたい
→ 上記コードを使えば、test_auth_integration.py から registration.registration を 直接import できるようになる！

registration.py は、「新しいユーザーを登録する」 ための 中心的な処理を担うファイルです。以下のような役割を果たしています：

【registration.py の役割】ユーザー登録の一括処理
1. 入力データの受け取りとチェック
python
Copy
Edit
username = registration_data.get("username")
email = registration_data.get("email")
password = registration_data.get("password")
ユーザーから送られた username, email, password を受け取り、未入力があれば例外を出す。

2. UUID（ユーザーID）の発行
python
Copy
Edit
user_uuid = str(uuid.uuid4())
一意な ID（UUID）を発行して、登録するユーザーを一意に識別できるようにする。

3. パスワードの安全な保存準備
python
Copy
Edit
salt = generate_salt()
password_hash = hash_password(password, salt)
ソルトを生成し、パスワードをハッシュ化することで、DynamoDB に安全に保存できる形式にする。

4. クライアント証明書の発行
python
Copy
Edit
cert_bytes, cert_fp = generate_client_certificate(user_uuid)
client_cert.py の関数を使って、暗号鍵ペアと証明書（ダミー or 実証明書）を生成し、

証明書のフィンガープリント（SHA256）も取得する。

5. ユーザー情報を構築し、DynamoDB に保存
python
Copy
Edit
user_item = {...}
save_user_to_dynamodb(user_item)
上記で準備したデータ（UUID, ハッシュ, 公開鍵, フィンガープリントなど）をまとめて、

db_integration.py 経由で DynamoDB に保存する。

6. SNS通知（オプション）
python
Copy
Edit
notify_user_via_sns(...)
登録完了を SNS 経由で通知したい場合に使用（エラーが出る場合は無効化してもOK）。

7. クライアントに返すレスポンス（証明書のBase64付き）
python
Copy
Edit
return {
    "success": True,
    "uuid": user_uuid,
    "client_cert": base64.b64encode(cert_bytes).decode("utf-8"),
    "message": ...
}
クライアントに返す情報として、

uuid

Base64形式のクライアント証明書

成功メッセージ を含めて返す。

まとめ：registration.py がやっていること
ステップ	処理	使用するモジュール・関数
①	入力チェック	registration_data.get()
②	UUID 発行	uuid.uuid4()
③	パスワード処理	generate_salt, hash_password
④	証明書発行	generate_client_certificate
⑤	ユーザー保存	save_user_to_dynamodb
⑥	SNS通知（任意）	notify_user_via_sns
⑦	クライアントへレスポンス	Base64変換して返却
もし「JWTの発行」や「ログイン認証」は？と聞きたくなるかもしれませんが、それは login.py が担当 します。registration.py はあくまで「登録（保存）」に集中しています。


✅salt_bytes 最終方針まとめ

項目	    処理
saltの型	登録時: bytes / 保存: hex(str) / 読込: bytes.fromhex()
hash関数	hash_password(password, salt_bytes)
DynamoDB保存	saltは hex文字列 で保存


# test 環境設定
$env:PATH = "D:\Python\Python314;" + $env:PATH
python --version
にて、powershellでpython314を使えるようにしておく。

# test error
以下のログから読み取れるエラーは主に以下の種類になります。

■　DeprecationWarning (非推奨警告)
例：
DeprecationWarning: datetime.datetime.utcnow() is deprecated … Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC)
意味：
現在のコードで datetime.utcnow() を使っていますが、これは将来的に削除される予定です。代わりに datetime.now(timezone.utc) など、タイムゾーン情報を持つUTC表現を使用するように推奨されています。

対策：
すでにコード中では datetime.now(timezone.utc) に変更している箇所もあるので、ライブラリ内部（botocoreなど）の警告であれば、将来的なアップデートを待つか、非表示にする設定を行う（テスト環境などの場合）。

■　SNS Notification Error
例：
SNS notification error: An error occurred (InvalidClientTokenId) when calling the Publish operation: No account found for the given parameters
意味：
SNS にメッセージを発行しようとした際に、AWS アカウントやクレデンシャルの問題により、認証情報が正しくない、またはアカウントが見つからないというエラーです。

対策：
・テスト環境では、環境変数 SNS_TOPIC_ARN を "dummy" と設定し、実際の SNS 発行処理をスキップするようにする。
・本番環境では、正しい AWS クレデンシャルおよび SNS トピックARNが設定されているか確認してください。

■　ログインエラー：Client certificate fingerprint mismatch
例：
ログインエラー: Client certificate fingerprint mismatch
意味：
ユーザーのログイン時に、入力されたクライアント証明書のフィンガープリントが、登録されているものと一致しない場合に発生します。証明書が改ざんされているか、ユーザーが間違った証明書を使っている可能性があります。

対策：
登録時に保存されるフィンガープリントと、ログイン時に送信されるフィンガープリントの取得・比較処理を見直し、一致するかどうかを確認する処理のロジックをチェックしてください。

■　ログインエラー：Password does not match
例：
ログインエラー: Password does not match
意味：
ユーザーがログイン時に入力したパスワードをハッシュ化した結果と、DynamoDB などに保存されているパスワードハッシュが一致しない場合に発生します。入力ミスや、パスワード保存処理の不具合が考えられます。

対策：
パスワードのハッシュ化の処理、ソルトの取り扱い、比較処理（hmac.compare_digest の利用など）を見直してください。

■　登録エラー：必須フィールド不足
例：
登録エラー: username, email, and password are required
意味：
ユーザー登録時に必須項目（username、email、password）が送信されていない場合に発生します。

対策：
クライアント側の入力チェックや、API 側で受信したデータのバリデーション処理を強化してください。

これらのエラーは、各機能（証明書発行、SNS通知、パスワード検証、入力データのバリデーション）に関連しています。ログの内容に合わせ、各箇所の処理ロジックや環境設定を再確認してください。

以上がログに現れている主なエラーの種類と、それぞれの意味・対策です。必要に応じて、コードの該当箇所を修正・デバッグしてみてください。

# test error 2
・まずはpython app_registration.pyを実行してサーバーを起動。
・次に　pytest -v test_registration.pyを実行してテスト。

しかし、URLがどうしても読み込めなかった。local5000,さらには127.0.0.1.5000などしたけどだめ。
結局は下記のようにしたらエラーが出ずだった。要注意！
def test_registration_post_no_data():
    """
    POST /registration/ ボディなし → 400エラーになるかテスト
    """
    url = "http://192.168.3.8:5000/registration/"
    　　　（※）registration/ ←　末尾の/は必須なので要注意！

# test error 3
scanのエラーが止まらない。どうしたらいいか。
エラーの原因
ClientError: An error occurred (ValidationException) when calling the Scan operation:
Invalid FilterExpression: Attribute name is a reserved keyword; reserved keyword: uuid
つまり：
uuid は DynamoDB の予約語なので、直接 FilterExpression に使えない！

✅ 修正方法
DynamoDB では予約語（例: uuid, name, size など）を使いたい場合、Expression Attribute Names を使って名前をバイパスします。
🔧 修正後のコード
resp_scan = devices_table.scan(
    FilterExpression="#u = :u",
    ExpressionAttributeNames={"#u": "uuid"},
    ExpressionAttributeValues={":u": test_user_uuid}
)


#　dilithium5 を埋め込んだので、python312でのサーバー起動は下記から
# まずはpython312に各種インストール
作業	具体例
3.12のPython.exeを確認	（なければインストール）
D:\Python\Python312\python.exe -m venv D:\city_chain_project\.venv312
作ったあと、
D:\city_chain_project\.venv312\Scripts\activate.bat
という具合に、仮想にはいること。

D:\Python\Python312\python.exe -m pip install flask flask-cors requests boto3 qrcode pytest PyJWT cryptography pillow qrcode[pil]

これにより、Python 3.12 環境でテストが実行され、既にインストール済みの Pillow（PIL）が利用されるはずです。


そうすると、下記のようにパスする！
====================================================== test session starts =======================================================
platform win32 -- Python 3.14.0a4, pytest-8.3.4, pluggy-1.5.0 -- D:\Python\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\login\registration
plugins: asyncio-0.25.3
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collected 6 items

test_registration.py::test_registration_get PASSED                                                                          [ 16%]
test_registration.py::test_registration_post_success PASSED                                                                 [ 33%]
test_registration.py::test_registration_post_no_data PASSED                                                                 [ 50%]
test_registration.py::test_registration_post_missing_fields PASSED                                                          [ 66%] 
test_registration.py::test_qr_secondary_device_registration_success PASSED                                                  [ 83%]
test_registration.py::test_qr_secondary_device_registration_invalid_qr PASSED                                               [100%] 

======================================================== warnings summary ======================================================== 
test_registration.py::test_registration_get
  D:\Python\Python314\Lib\site-packages\pytest_asyncio\plugin.py:1190: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

test_registration.py::test_qr_secondary_device_registration_success
test_registration.py::test_qr_secondary_device_registration_success
test_registration.py::test_qr_secondary_device_registration_success
  D:\Python\Python314\Lib\site-packages\botocore\auth.py:425: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    datetime_now = datetime.datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================= 6 passed, 4 warnings in 7.97s ================================================== 
PS D:\city_chain_project\login\registration> 


あなたの設計方針（QRコードにはパスワードを含めない → DBで認証する）は 正しいアプローチ ですが、いま起きているエラーは**設計ミスではなく、“エラー処理が不足していた”**というのが正解です。

✅ 結論
設計は正しい。
QRコードに含めるのは uuid と fingerprint のみでよく、
username + password はフォーム or JSON で別送信する運用でOK。

現在の実装では、username や password が None の場合、エラーメッセージが "username, email, and password are required" に統一されてしまっている。
→ これが混乱の元です。

🔍 エラーの原因の整理
今のコード（register_user 関数の一部）
qr_code = registration_data.get("qr_code")
logger.info(f"受け取ったqr_code: {qr_code}")

if qr_code:
    # 2台目端末のロジック
    return register_second_device_via_qr(qr_code, registration_data)

# 新規ユーザー登録のチェック
username = registration_data.get("username")
email = registration_data.get("email")
password = registration_data.get("password")
if not username or not email or not password:
    raise Exception("username, email, and password are required")
☠️ 問題点：
QRコードがある → register_second_device_via_qr に分岐しているのに、
username や password がなかったら そのあとで エラーが出る。

✅ 修正方法（明示的に切り分ける）
📁 修正ファイル：
registration/registration.py

🛠 修正箇所：
def register_user(registration_data) の中のこの部分を下記のように修正してください：

✅ 修正後のコード（安全な分岐処理）👇
python
Copy
Edit
def register_user(registration_data: dict) -> dict:
    """
    ユーザー登録処理（新規 or 2台目）
    """
    qr_code = registration_data.get("qr_code")
    logger.info(f"受け取ったqr_code: {qr_code}")

    if qr_code:
        # 🔒 安全にusername / password を検証
        username = registration_data.get("username")
        password = registration_data.get("password")
        if not username or not password:
            raise Exception("2台目端末登録には username と password が必要です")

        # 分岐して2台目登録
        return register_second_device_via_qr(qr_code, registration_data)

    # ▼ 新規登録ルート ▼
    username = registration_data.get("username")
    email = registration_data.get("email")
    password = registration_data.get("password")
    if not username or not email or not password:
        raise Exception("username, email, and password are required")
🧠 補足：なぜこれが必要なのか？
このようにQRコードがあるかどうかで処理を早期分岐しないと、

JSONに "qr_code" だけ入ってて、"email" がない場合も、

無関係な "username, email, and password are required" のエラーが返る

という 不正確なメッセージ になってしまうのです。


# フローイメージ
      1台目登録                2台目登録
┌────────────┐           ┌─────────────────────┐
│register_user│─┐ QR ─▶ │register_second_device│
└────────────┘ │         └─────────────────────┘
                │             ▲ 4. 新規 PEM & 鍵発行
                │             │ 5. DevicesTable 保存
   2. QR = uuid,fingerprint   │ 6. PEM+鍵 を端末へ返す
                │             ▼
          スマホカメラ      端末専用クライアント証明書

1 台目 : ユーザー専用 PEM を発行し、fingerprint を QR 化。

2 台目 : QR で本人確認 → 端末専用 PEM をその場で発行し返却。

これで各端末が 個別のクライアント証明書 を持ち
Dilithium/NTRU 秘密鍵も端末側にだけ配布
という構成になります。

方針まとめ

目的	変更点
複数端末 (n 台) を安全に登録	- 端末ごとに新しいクライアント証明書を発行
- DevicesTable に「端末ごとの fingerprint」を保存
QR コード流出対策	- ワンタイムの Pairing-Token を発行し、それを QR に埋め込む
- Token は DynamoDB に TTL 付き保存 (10 分／1 回使い切り)
登録フロー	1. 1 台目が「端末追加」ボタン → /registration/request_pairing_token を呼ぶ
2. サーバが Token を DynamoDB に保存し、uuid & token の QR を返す
3. 2 台目がスキャン → /registration/ に qr_code + username + password を POST
4. サーバは Token を検証 → 新しい証明書 を発行 → DevicesTable へ登録


#　まとめ
フロント側 (例: Vue / React / JS) ワークフロー
(ログイン済み画面)
↓
1. 端末追加ボタン
   → currentlyLoggedinFingerprint を localStorage から取得
   → POST /registration/request_pairing_token
        { username, password, client_cert_fp }
↓
2. サーバが OK ⇒ qr_code を返す
   → Canvas に表示 or /print
↓
3. 新端末がスキャン → register_second_device_via_qr() へ
ポイント

「どの端末が親か」の概念をなくし “登録済み端末 + 正しい資格情報” を親とみなす

認証に “何を足すか” は要件に応じて：

生体認証 + WebAuthn

TOTP (Google Authenticator)

デバイスのクライアント証明書＋署名チャレンジ

これで “1 台目が壊れた／盗まれた” 場合も、残った端末でペアリングトークンを発行できますし、
QR コードだけ盗まれても 登録済み fingerprint が一致しなければトークン自体が発行されません。

#　ファイル	変更タイミング	やること
registration/pairing_token.py	❶ 追加済み	そのまま
registration/routes.py	❷ でエンドポイントを追加 → ❸ でロジックを更新	同じ関数を最新版に書き換える
（fingerprint チェックと 403 を入れる）
すでに ❷ のコードがあるなら、該当関数部分だけ 前ターンで示した最新版に置き換えてください。
それ以外のコード（import、他のルート、register まわり）はそのままで大丈夫です。

これで pairing_token の実装と fingerprint による本人端末確認 が一貫します。