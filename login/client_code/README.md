整理すると、二つの役割があります。

1. クライアント側（pc_check.py）
ensure_dummy_file() で常に 100 MB のダミーファイルを生成してディスクを占有
測定: その状態で shutil.disk_usage から空き容量を取得
POST: client_free_space と認証情報を /device_auth/login に送信
認証成功時 にダミーファイルを 削除 して領域を開放

これで、常にログイン前に 100 MB を確保し、ログイン成功後に解放するワークフローが実現できます。

2. サーバー側ユーティリティ（user_manager/utils/）
a) platform_utils.py
HTTP ヘッダ（User-Agent か X-Device-Type）を解析して、
"pc" | "iot" | "android" | "ios" | "game" | "tv" | "car" | "unknown" のいずれかを返す関数を提供。

b) storage_checker.py
プラットフォーム種別ごとに
PC/IoT → サーバー自身のディスク空き容量を shutil.disk_usage("/") でチェック
それ以外 → （テスト時は）常に OK またはクライアント送信の client_free_space を使う
というロジックを提供。

c) app_utils.py （テスト用 Blueprint）
上記 a, b をエンドポイント化して
GET /utils/detect_platform → プラットフォーム種別を JSON で返す
GET /utils/check_storage → サーバー側ディスクチェックのみを JSON で返す
本番フローではこちらはあくまで「動作確認用」。

3. 最終的なログインフロー
クライアント (pc_check.py) がダミーファイル生成 → 空き容量取得 → /device_auth/login に POST
サーバーのデバイス認証 Blueprint (login/user_manager/utils/login_handler.py) が
detect_platform_from_headers() でプラットフォーム判定
PC/IoT → check_server_disk_usage("/")
その他 → クライアント送信の client_free_space
ストレージ OK なら auth_py.login.login_user() で本来の認証
認証結果（200, success: true）を返す
クライアントが成功レスポンスを受け取ったら remove_dummy_file() でファイルを削除

これで、
常にログイン前に 100 MB 占有
ログイン成功で解放
失敗時は保持
という要件を満たす、セキュアかつテスト可能な仕組みになります。

まとめ:
dummy_copy.kt に保存した一連のファイル群により、下記のことが実現される。

このフローでは、
LoginActivity でサーバーに認証リクエストを送る
サーバーが LoginResponse（success フラグと必要に応じて rsaPrivateKey 等）を返す
クライアントは KeyStoreManager.ensureKeyPair() を呼んで端末の Android KeyStore に RSA 鍵ペアを生成・保存
FileManager.reserveSpace() で端末に 100 MB の予約ファイルを作成
StorageApiService.storageCheck() で「100 MB 確保しましたよ」という通知を User Manager 側の /user/storage_check エンドポイントへ送信
正常ならメイン画面へ遷移し、ログアウト時に FileManager.releaseSpace() でファイルを削除

という流れが一気通貫でつながります。
──つまり「ログイン成功 → 端末上に鍵を保存（KeyStore）→ 100 MB 予約 → サーバーへ通知 → メイン画面へ」という一連の処理になっていて、ご認識のとおりです。


ClientApp/
├── app/
│   ├── build.gradle
│   ├── src/
│   │   ├── main/
│   │   │   ├── AndroidManifest.xml
│   │   │   ├── java/com/example/app/
│   │   │   │   ├── network/
│   │   │   │   ├── security/
│   │   │   │   ├── storage/
│   │   │   │   └── ui/
│   │   │   └── res/layout/
│   │   │       ├── activity_login.xml
│   │   │       ├── activity_main.xml
│   │   │       └── activity_logout.xml
├── build.gradle
├── settings.gradle


以下のようにクライアント端末には合計５種類の鍵・証明書を持たせるイメージになります。

1. 起動時の準備フェーズ
RSA 鍵ペア生成

用途１：サーバーから送られてくる Dilithium 秘密鍵を暗号化／復号するため
Kotlin／Java で
val rsaKeyPair = KeyPairGenerator.getInstance("RSA").apply {
  initialize(2048)
}.genKeyPair()
// rsaKeyPair.private → rsa_private_key.pem
// rsaKeyPair.public  → rsa_public_key.pem （Base64 PEM 形式でサーバーに渡す）
保存先：filesDir/rsa_private_key.pem（秘密鍵）、filesDir/rsa_public_key.pem（公開鍵）

NTRU＋Dilithium 鍵ペア生成

用途２：クライアント証明書の SubjectPublicKeyInfo に埋め込むため
Android ならネイティブライブラリ呼び出しで
val keys = ClientKeygen.generateClientKeys()
// keys.ntru_private, keys.ntru_public
// keys.dilithium_private, keys.dilithium_public
保存先：
filesDir/ntru_private_key.pem
filesDir/ntru_public_key.pem
filesDir/dilithium_private_key.pem
filesDir/dilithium_public_key.pem
TLS Mutual-Auth 用証明書取得

用途３：HTTPS 通信でクライアント認証（RSA/ECDSA ベース）
端末内で CSR を作ってサーバーに送り、CA が返した client_tls_cert.pem と対応する秘密鍵 client_tls_key.pem を受け取って保存
保存先：
filesDir/client_tls_cert.pem
filesDir/client_tls_key.pem

2. クライアント証明書（PQC 証明書）取得フェーズ
POST /client_cert に対して、先ほど生成した
{
  "uuid": "ユーザーID",
  "ntru_public_b64": "<Base64でエンコードした NTRU 公開鍵>",
  "dil_public_hex":  "<HEX文字列の Dilithium 公開鍵>"
}
サーバー CA 側で SPKI の algorithm OID に NTRU／parameters に Dilithium を埋め込んだ X.509 PEM を発行
返却された PEM（client_certificate.pem）を
保存先：filesDir/client_certificate.pem

3. Dilithium 秘密鍵受け取りフェーズ
クライアントが /user/keys/update エンドポイント（ユーザーキー更新）を呼び、
リクエスト JSON に
{
  "user_uuid":   "...",
  "rsa_pub_pem": "<先に生成した rsa_public_key.pem の文字列>"
}
サーバー側で新しい Dilithium 鍵ペアを作成し、

公開鍵を DDB に保存
秘密鍵を rsa_pub_pem で暗号化し Base64 で返却
クライアントは返ってきた encrypted_secret_key を
val cipherBytes = Base64.decode(encrypted_secret_key, Base64.DEFAULT)
val priv = loadPemPrivateKey("rsa_private_key.pem")
val plainHex = priv.decrypt(cipherBytes, …)
val dilSecBytes = hexStringToByteArray(plainHex)

と復号し、
保存先：filesDir/dilithium_secret_key.pem

4. 通信メッセージ署名フェーズ
毎回の API 呼び出し等に対しては、
dilithium_secret_key.pem を読み込んで
val sig = DilithiumSigner.sign(message.toByteArray(), dilithiumSecretKey)

を使い、HTTP ヘッダや JSON に載せて改ざん検知を行います。

まとめると
種類	ファイル名 on 端末	用途
RSA 鍵ペア	rsa_private_key.pem / rsa_public_key.pem	Dilithium 秘密鍵の暗号化・復号
NTRU＋Dilithium 鍵ペア	ntru_.pem / dilithium_.pem	クライアント証明書（SPKI）発行用
TLS Mutual-Auth 証明書	client_tls_cert.pem / client_tls_key.pem	HTTPS クライアント認証
クライアント証明書（PQC 証明書）	client_certificate.pem	NTRU＋Dilithium 公開鍵入り X.509 PEM
暗号化された Dilithium 秘密鍵	dilithium_secret_key.pem	メッセージ署名

秘密鍵 はすべてアプリのプライベート領域（context.filesDir など）に閉じ込め、決して外部へ漏らさないこと。
公開鍵・証明書 は必要に応じてサーバーへ提出したり、端末間で共有したりしますが、改ざん防止のため保護されたストレージに置いてください。


✅ 次のステップ候補
もしログイン〜保存が確認できたら、次のような機能も追加できます：

機能	説明
🔐 鍵の削除	Logout 時に秘密鍵・証明書・予約ファイルを削除
♻️ 証明書の自動更新	有効期限に近づいたら再発行処理を行う
❌ 紛失時の失効処理	2台目端末追加トークンや管理者 UI から、特定証明書を失効させる
📱 biometrics 認証連携	秘密鍵保存や復号に生体認証を要求（Android Keystore連携）


# なぜ「クライアントで署名」が要るのか ── 設計をいったん言語化します
フェーズ	どこで何が起きる？	目的
登録 (/user/keys/update)	サーバ
1. Dilithium 鍵ペアを生成
2. Public-Key は DynamoDB に保存
3. Secret-Key を RSA で暗号化しクライアントへ返す	「クライアントだけが秘密鍵を持つ」状態を作る
ログイン後	クライアント (Android)
1. 受け取った encrypted_secret_key_b64 を RSA で復号
2. 復号した raw Dilithium Secret-Key を 安全領域（Keystore など）に保存	以降はネットワーク要求ごとに署名を付けられる
API 呼び出し	クライアント → サーバ
HTTP ヘッダ X-Signature などに Dilithium 署名 を付与	サーバは保存済み Public-Key で検証し、改竄 & なりすましを防ぐ

🔑 ポイント
サーバは Public-Key を既に持っているので、クライアントから PEM を送り返す必要はありません。
クライアントは「毎回、要求本文かチャレンジ文字列に対して署名を作って送る」役目です。

エラーが示すもの
UnsatisfiedLinkError: … DilithiumSigner$DilithiumNative.sign …
Dilithium 署名を呼び出したが JNI レイヤーに実装が無い
→ だからテストも実行時も落ちている。

サーバとの通信自体は 署名無しでも動くエンドポイント（たとえば /login 自体）なら
今のままでも試せますが、署名必須の API に行った瞬間に 401/403 になります。

選択肢は 2 つ
目的	方法	メリット / デメリット
A. まずアプリをクラッシュさせず開発を進める	「ダミー署名 (= 単に msg を返すだけ)」を JNI で実装し、サーバ側で 署名検証を一時的に無効化 または skipSignature=true のようなフラグを付けておく	早く UI や他の機能を試せる / ただし本番には使えない
B. 本物の Dilithium 署名を実装する	・PQClean C 実装を NDK に取り込む
・または Rust (pqcrypto) を NDK 用 .so にクロスビルドして JNI ラッパを書く	セキュア & 本番そのまま / 実装コストが大きい

**「RSA だけでいいのでは？」**と思いがちですが
RSA で渡すのは「秘密鍵を安全に“配送”するため」だけで、メッセージ署名には不向き
（鍵長・速度・耐量子性の要件を満たさない）という理由で二段構えにしています。