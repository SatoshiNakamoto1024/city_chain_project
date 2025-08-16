サーバー側の修正が完了したので、次は Android端末にクライアント証明書と秘密鍵を保存する手順 を丁寧に説明します。

✅ 目標（確認）
最終的に端末側には以下のファイルが保存されます：

保存対象	保存先ファイル名
クライアント証明書 PEM	client_certificate.pem
NTRU秘密鍵 PEM	ntru_private_key.pem
Dilithium秘密鍵 PEM	dilithium_private_key.pem
Dilithium秘密鍵 RAW	dilithium_secret_key.pem（rawバイト列）
RSA秘密鍵 PEM	rsa_private_key.pem（AndroidKeyStore or files）

🛠 実行手順（1つずつ）
① Android端末にアプリをビルドしてインストール
✅ 実施方法
Android Studio を使って LoginActivity.kt を含むアプリをビルドし、実機またはエミュレータにインストールします。

② サーバーを起動（registration Flaskアプリ）
✅ 実施方法
# Anaconda や venv を有効化した状態で
cd D:/city_chain_project/login/registration
python app_registration.py
これで http://localhost:5000 で Flask アプリが起動します。
Android 側の BASE_URL = "http://192.168.3.8:5000" にマッチしていればOK。

③ Androidアプリを起動し、ログイン画面でIDとパスワードを入力
✅ 入力する内容（登録済みユーザー）
Username: testuser1
Password: TestPass123!
または、事前に /registration/ に POST してユーザー登録した内容に合わせてください。

④ LoginActivity.kt の動作の流れ（自動処理）
ステップ	処理内容
①	AuthApiService.login() を実行 → /user/login へ POST
②	サーバーから clientCertificatePem, ntruPrivateKeyPem などが返る
③	KeyFileManager.storeAll(...) が呼ばれ、それぞれの PEM をファイル保存
④	RSA鍵ペアの読み込み・作成 → 公開鍵を使って updateKey() を呼び出す
⑤	サーバーから受け取った RSAで暗号化されたDilithium秘密鍵 を復号
⑥	DilithiumSecretKeyStore.save() によって raw秘密鍵をファイル保存
⑦	FileManager.reserveSpace() で 100MB の予約ファイルを作成
⑧	/user/storage_check に通知（予約サイズ送信）
⑨	MainActivityに遷移

⑤ 保存されたファイルの確認方法（実機 or エミュレータ）
✅ Android Studio > Device File Explorer
パス: /data/data/com.example.test100mb/files/

中に以下のファイルがあるはずです：
client_certificate.pem
ntru_private_key.pem
dilithium_private_key.pem
dilithium_secret_key.pem
rsa/rsa_private_key.pem
rsa/rsa_public_key.pem
reserve.bin
🎯 補足：もし保存されていなかったら
ログインに失敗していないか（ステータスコード401など）

KeyFileManager.storeAll() や DilithiumSecretKeyStore.save() が try-catch によって黙殺されていないか

Device File Explorer で files/ 配下にファイルが生成されているか

/user/login に対してサーバー側が正しい証明書＋鍵を返しているか

✅ 完了チェックリスト
 /user/login で証明書と鍵が返ってくる

 Android でそれらをファイルとして保存できている

 MainActivity に遷移できている（＝ログイン成功）

必要であれば次に「ログアウト処理時に鍵を削除」「証明書の自動更新処理」「端末紛失時の失効処理」などを組み込めます。
希望があれば、その手順も続けてご案内します！
