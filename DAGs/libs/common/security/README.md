じゃあ、セキュリティのモジュール化は何処に入れる？セキュリティと言っても幅広い。手段は大きく3つだよね？クライアント証明書、サーバー証明書、データ暗号化。通信箇所は限定されるね、mongoDBに保存時、ノード間通信、あとはログイン情報取得のためにDynamoDBに問い合わせ時、だよね？これらの通信セキュリティモジュール化はdappsにてクライアント証明書＋通信のdilithium署名を入れてるから、DAGにてもさらに入れた方がいい？モジュール化するなら、どこの通信をどう処理するかも詳細に記載して。

通信のセキュリティをきっちりモジュール化するなら、共通ライブラリとしてまとめておくのがベストです。
network/sending_DAG/python_sending/common/security/ パッケージを作り、そこに以下の３大フェーズごとのサブモジュールを配置します。

common/security/
├── __init__.py
├── app_security.py
├── config.py
├── certs.py            # 証明書（クライアント／サーバー）読み込み・検証ユーティリティ
├── mtls.py             # mTLS チャンネル／HTTP クライアント／サーバー設定ラッパ
├── signing.py          # Dilithium/NTRU 署名・検証ラッパ
├── encryption.py       # データ暗号化 (AES-GCM / CSFLE) ラッパ
└── tests/
    ├── test_certs.py
    ├── test_mtls.py
    ├── test_signing.py
    └── test_encryption.py

各モジュール詳細
1. certs.py
役割: X.509 PEM 証明書のロードと内容チェック。

load_pem(path) -> x509.Certificate

validate_chain(cert, trust_anchors) -> bool

get_cn(cert) -> str

2. mtls.py
役割: gRPC／HTTP クライアントとサーバーを mTLS–Ready に生成。

create_grpc_server(endpoint, certs: Certs, interceptors=[]) -> grpc.Server

create_grpc_channel(target, certs: Certs) -> grpc.Channel

create_https_session(certs: Certs) -> requests.Session

3. signing.py
役割: Dilithium（トランザクション署名）と NTRU（鍵ラップ）の一元インターフェース。

sign_message(msg: bytes, priv_key: bytes) -> bytes

verify_signature(msg, sig, pub_key) -> bool

wrap_key(pub, key) -> capsule

unwrap_key(priv, capsule) -> key

4. encryption.py
役割: アプリ内データを AES-GCM で暗号化／復号。

encrypt_field(plaintext: bytes, key: bytes) -> bytes

decrypt_field(ciphertext: bytes, key: bytes) -> bytes

create_data_key() -> (key_id, key_bytes) （CSFLE 用）

どの通信を守るか
dApps ↔ DAG エントリ（Flask/API）

TLS (HTTPS)＋Dilithium 署名付き JSON

mtls.create_https_session() でサーバーCERT検証＋クライアントCERT提示。

signing.sign_message() でリクエストペイロード署名、サーバー側で verify_signature()。

ノード間通信 (gRPC)

mTLS on gRPC

mtls.create_grpc_channel() ＋ certs.load_pem() からロードした CA/証明書で二者間認証。

DAG ↔ MongoDB

TLS (MongoDB URI オプション)

encryption.encrypt_field() でフィールドレベル暗号化 (CSFLE)

certs.load_pem() で MongoDB クライアント証明書を読み込んで ssl_certfile オプションに渡す

DAG/サービス ↔ DynamoDB

HTTPS (AWS SigV4) は AWS SDK が勝手にやってくれるので、mtlsモジュールではなく、
環境変数で AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を安全に管理。

使い方例（pseudo-code）

from common.security import certs, mtls, signing, encryption

# 1) Load your PEMs
my_certs = certs.load_pem("/path/to/chain.pem")

# 2) Build gRPC client to other DAGノード
channel = mtls.create_grpc_channel("nodeB:50051", my_certs)
stub = DAGServiceStub(channel)

# 3) Sign your payload before send
payload = json.dumps(tx).encode()
sig = signing.sign_message(payload, my_certs.priv_key)
stub.SubmitTransaction(TxRequest(tx=payload, signature=sig))

# 4) On receiving side, verify
if not signing.verify_signature(req.tx, req.signature, my_certs.pub_key):
    context.abort(StatusCode.UNAUTHENTICATED)

# 5) Before storing into Mongo, encrypt sensitive fields
encrypted_msg = encryption.encrypt_field(tx["message"].encode(), data_key)
db.coll.insert_one({**tx, "message": encrypted_msg})

# 6) When reading back
doc = db.coll.find_one(...)
doc["message"] = encryption.decrypt_field(doc["message"], data_key).decode()

こうまとめておくと、どの通信（Flask⇄DAG, ノード間 gRPC, DB 接続, AWS API）をどの手段（TLS/mTLS, 署名, 暗号化）でどのモジュール呼び出し（mtls, signing, encryption）で実現しているかが一目瞭然になります。これでセキュリティ要件のモジュール化は完了です。


# test
✅ 方法②：PYTHONPATH を通して絶対インポートにする
app_security.py に書いたインポート文：
from security import certs, mtls, signing, encryption
この security モジュールを認識させるには、親ディレクトリ（D:\city_chain_project\network\DAGs\common）を PYTHONPATH に含める必要があります。

ファイル冒頭にパスを通しておく：
import os, sys
sys.path.append(os.path.abspath("D:\\city_chain_project\\network\\DAGs\\common"))

つぎに、これもインストールしておく。
pip install python-multipart

そして、
python security\app_security.py


# 🔐 common.security パッケージ全体像
サブモジュール、	役割、	代表 API
config.py、	設定集中管理（環境変数とデフォルトパス）、	CLIENT_CERT_PATH, AES_MASTER_KEY …
certs.py、	PEM/X.509 のロード & チェック、	load_pem(), validate_chain()
mtls.py、	mTLS を簡単に使うためのラッパー、	create_https_session(), create_grpc_channel()
signing.py、	Post-Quantum & RSA 署名／検証 & NTRU KEM、	create_dilithium_keypair(), sign_rsa(), …
encryption.py、	フィールド暗号化（AES-GCM） & データキー生成、	encrypt_field(), decrypt_field(), create_data_key()
tests/*	単体テスト、（Dilithium/NTRU/RSA/AES & mTLS）、	pytest … で 100 % パス

<br>
1. 証明書ユーティリティ certs.py
from security import certs

crt = certs.load_pem("/path/node.crt")   # → cryptography.x509.Certificate
assert certs.get_cn(crt) == "node-A"

anchors = [certs.load_pem("/path/ca.crt")]
if not certs.validate_chain(crt, anchors):
    raise RuntimeError("certificate untrusted")

✦ 用途: クライアント／サーバー証明書の前検証・CN 抽出・チェーン検証。

2. mTLS ヘルパー mtls.py
・　HTTPS クライアント
from security import mtls

sess = mtls.create_https_session()        # ← config の証明書パスを自動利用
resp = sess.get("https://peer-node/ping")
CLIENT_CERT_PATH / CLIENT_KEY_PATH / CA_CERT_PATH が環境変数 or デフォルトパスにあれば自動で mTLS セッション。

verify=True が入るので改ざん CA 不可。

・　gRPC チャネル
channel = mtls.create_grpc_channel("peer-node:50051")
stub    = DAGServiceStub(channel)
reply   = stub.SubmitTransaction(TxRequest(...))
grpc.secure_channel() + grpc.ssl_channel_credentials(...) を隠蔽し、同じ証明書束を使い回し。

3. 署名 & KEM signing.py
アルゴリズム	主な関数	説明
Dilithium5 (PQ)	create_dilithium_keypair() / sign_dilithium() / verify_dilithium()	Tx ペイロード署名に採用
NTRU KEM (PQ)	create_ntru_keypair() / encap_ntru() / decap_ntru()	鍵配送（共有秘密鍵）
RSA-PKCS1v1.5	create_rsa_keypair() / sign_rsa() / verify_rsa()	従来ブラウザ互換・TLS 内部署名

例: Dilithium 署名
pk, sk = signing.create_dilithium_keypair()
payload = b'{"tx":"abc"}'
sig     = signing.sign_dilithium(payload, sk)

assert signing.verify_dilithium(payload, sig, pk)

例: NTRU KEM
pubB, secB = signing.create_ntru_keypair()
cipher, sharedA = signing.encap_ntru(pubB)   # A → B
sharedB = signing.decap_ntru(cipher, secB)   # B 側で復号

assert sharedA == sharedB                    # 共通鍵（32 byte）

例: RSA
priv, pub = signing.create_rsa_keypair(bits=2048)
sig = signing.sign_rsa(b"hello", priv)   # sig は生バイト列
assert signing.verify_rsa(b"hello", sig, pub)
sign_rsa() は 生 署名を返す。必要なら base64.b64encode() で文字列化。
verify_rsa() は bytes / Base64 どちらでも受け付け。

4. フィールド暗号化 encryption.py
from security import encryption

# データキー（AES-GCM 256bit）を発行し DB に保管
key_id, key_bytes = encryption.create_data_key()

cipher = encryption.encrypt_field(b"secret", key_bytes)
plain  = encryption.decrypt_field(cipher, key_bytes)
assert plain == b"secret"
AES-GCM で iv | tag | ciphertext をひとまとめにバイト列化。

MongoDB へ保存 → 取り出し時は decrypt_field() 呼び出し。

5. FastAPI デモ app_security.py
python -m network.DAGs.common.security.app_security
/sign/dilithium – POST {payload} → 署名返却

/verify/dilithium – POST {payload, signature, pub} → bool

/enc/field – POST {plaintext} → ciphertext

/dec/field – POST {ciphertext} → plaintext

→ Quick REPL として使えるので連携テストが楽。

6. テスト & CI
pytest network/DAGs/common/security/tests -q
....  (4 passed)
Dilithium / NTRU / RSA / AES & mTLS の基本動作を保証。

CI で「暗号 API 互換性」が壊れても即座に検知。

#　運用ベストプラクティス
証明書の配置
/etc/ssl/
  ├── client.crt
  ├── client.key
  └── ca.crt
置換したい場合は環境変数で再定義。

キー管理
データキーは KMS or HSM でラップし、key_id と一緒に MongoDB に保存。
Dilithium/NTRU の秘密鍵は必ず 外部保管 or HSM でロード。

ローテーション
RSA → PQ への段階的移行時は verify を二重化 し、どちらかが pass すれば OK にすることでゼロダウンタイム切替が可能。

これで DAG ネットワーク全体の機密性・完全性・真正性 を、
最小限の呼び出しコードで確実に担保できます ✅