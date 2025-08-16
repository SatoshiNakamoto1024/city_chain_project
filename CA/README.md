
✅ 「クライアント証明書をNTRUで発行している」部分とは？
主なファイルと関数

ファイル	関数	内容
client_cert/client_keygen.py	generate_client_keys()	NTRUとDilithium鍵ペアを生成
client_cert/cert_builder.py	build_client_certificate(...)	NTRU公開鍵＋その他メタデータを集約
ca/ca_signer.py	sign_certificate(...)	証明書データ全体に dilithium秘密鍵で署名
client_cert_api.py	/issue_cert API	上記を連携し、JSON形式で証明書と秘密鍵を返却

✔ 実際の「発行される証明書」の中身（例）
{
  "uuid": "xxxx-xxxx",
  "ntru_public": "ABCDEF123456...",        // ★ ここがNTRU公開鍵
  "dilithium_public": "789ABCDEF...",
  "valid_from": "2025-04-22T08:00:00Z",
  "valid_to": "2026-04-21T08:00:00Z",
  "issuer": "CustomCA v1",
  "signed_at": "2025-04-22T08:00:05Z",
  "signature": "これはNTRU秘密鍵で暗号化されたデータ"
}

つまり、証明書の構成要素は：
NTRU暗号鍵（暗号用途）
Dilithium署名鍵（署名用途）
署名付き（CA私鍵で署名） となっています。

✅ なぜ「数十行」なのか？（＝良い意味）
あなたが「複雑なアルゴリズムかと思ったが、数十行で完結していて驚いた」と感じたのは自然です。

✔ 理由：
暗号ロジック（NTRU/Dilithium）自体は別モジュール（例：ntru.ntru）にカプセル化されている
実際の難解な数式や多項式処理は、RustやCライブラリで処理され、Pythonではシンプルに使えるAPIになっている。
証明書は実は「構造体」+「署名」
通常のX.509証明書も「Subject, Issuer, 公開鍵, 有効期限」＋署名からなっており、本質的にはJSONでも簡潔に記述できる。
署名付きJSONという構成が現代的
JWSやVerifiable Credentialなどでも「署名付き構造化データ」という考え方が主流。

✅ 今後の選択肢（拡張性）

拡張アイデア	説明
PEM形式に変換	OpenSSL互換形式で外部連携も可能に（ASN.1エンコード）
QRコード化	発行証明書全体をbase64してQRで持ち歩く
JSON-LD + VC準拠	DIDやW3C準拠証明書に進化させる道もあり
AWS KMS にCA秘密鍵を保存	本番では署名操作のみKMSに委譲することで安全性向上

✅ 結論
今の構成は「軽量」「モダン」「拡張性あり」
クライアント証明書としての必要条件はすべて満たしており、
実用上は 非常にシンプルなコードで十分安全に運用 できます。


#　 どこで「CA から認証」を受けているか？
受けていません（開発用ダミー実装）

client_cert.py::generate_client_certificate() で

app_dilithium.create_keypair() から公開鍵／秘密鍵を生成

issuer に CA_NAME を書き込み

signature に固定文字列 "CA_SIGNATURE_PRODUCTION" を置く

実運用ならここで ルート CA の秘密鍵で X.509 署名しますが、
現状は メタデータとして CA 名を埋めるだけ です。

2. 証明書発行の詳しいステップ
app_client_cert.py /client_cert
手順	場所	目的
① リクエスト受信	/client_cert?uuid=…	UUID 必須、既発行なら再利用
② generate_client_certificate() 呼び出し	client_cert.py	- Dilithium 鍵ペア生成
- valid_from / valid_to 設定
- serial_number 生成
- JSON を bytes 化 & fingerprint 計算
③ S3 に保存	client_cert/<uuid>_<timestamp>.json	証明書本体 (公開鍵・秘密鍵含む) を長期保存
④ DynamoDB にメタ保存	テーブル ClientCertificates	参照しやすいようにメタだけ行で持つ
revoked フラグなどもここに
⑤ ローカルにもコピー	login_data/user_client_cert/… など	オフラインバックアップ／開発用確認
⑥ Base64 エンコードしてレスポンス	client_cert フィールド	クライアントが直接 JSON を取得したい場合用


#　D:\city_chain_project\CA\ を作成して、そこにさまざまなコードを作成するのはどう？
ChatGPT said:
Reasoned for 12 seconds
D:\city_chain_project\CA\ のような専用フォルダに、認証局（CA）のコードや管理ツールを分離して配置するのは、非常に合理的なアプローチです。これにより、以下のメリットが得られます。

1. セキュリティの向上
分離によるリスク低減:
CA のコードや秘密鍵管理、証明書発行などは非常に重要な機能です。アプリケーションコードと物理的に分離することで、万が一アプリケーション側に脆弱性があっても、CA の機密情報に直接アクセスされるリスクを低減できます。

アクセス制御:
専用フォルダ内のシステムは、内部ネットワークや専用の管理環境（VPN、物理的に隔離されたサーバーなど）に配置し、外部から直接アクセスできないようにすることが可能です。これにより、管理用インターフェースや証明書発行処理をより厳重に保護できます。

2. 運用と管理の効率化
モジュール化:
CA の機能は、証明書の発行、失効管理、更新、監査ログの取得、さらにはHSMとの連携など、複数のコンポーネントから成り立ちます。専用のフォルダにこれらをまとめておくことで、各機能が独立して開発・テスト・運用しやすくなります。

専用管理ツールの構築:
CA の管理画面（管理コンソール）を作成し、発行済み証明書の一覧表示、失効操作、証明書の有効期限管理などの処理を内部向けに実装できます。これにより、管理者は安全なネットワーク経由でCAの運用状況をリアルタイムに監視・操作できます。

将来の拡張性:
別フォルダにすることで、将来的に認証局専用のAPIやCLIツール、Webコンソールなどを追加しても、アプリケーションコードと独立してメンテナンスが可能です。

3. 技術的な実装の例
例えば、D:\city_chain_project\CA\ 配下に以下のような構成でコードを配置するイメージです：

makefile
Copy
D:\city_chain_project\CA\
├── cert_issuer.py       # 証明書発行のロジック（鍵ペア生成、署名、証明書データ生成）
├── ca_manager.py        # CA全体の運用・管理用ロジック（証明書の失効、更新、監査ログ）
├── config.py            # CAの設定ファイル（有効期限、CA名、HSMの設定など）
├── app_ca.py            # CA管理用のWebアプリケーション（管理画面、API）
└── tests\
    └── test_ca.py       # CAモジュールの単体テスト
このようにすることで、CAの運用に関するすべてのコードや設定を一箇所にまとめ、セキュリティ・管理性・拡張性を高めることができます。

結論
CA は本番環境で非常に重要な役割を果たすため、専用フォルダ（例えば D:\city_chain_project\CA\）にコードをまとめ、管理専用の環境やツールを構築するのは推奨される方法です。
この方法であれば、外部からのアクセスリスクを抑え、セキュアな運用を実現しやすくなります。

もし実際にこの方針で進める場合は、上記のようなフォルダ構成やファイル設計を参考に、CA管理システムの設計・実装を進めるとよいでしょう。


# 開発時の対処法
開発段階では、利便性のためにローカル環境で Web UI を利用して操作や確認ができるようにするのは一般的です。しかし、本番運用に移行する際は、以下の点に注意してください。

開発時はローカル環境で Web UI を利用:
ローカルの開発環境では、client_cert_ui() を有効にして、ブラウザから証明書の状態や操作結果を確認するのは便利です。
def client_cert_ui():
    """
    CA 管理画面（Web UI）を返す。templates/client_cert.html を利用。
    """
    return render_template("client_cert.html")

ただし、本番では必ずアクセス制限を行うか、Web UI を廃止して CLI などのセキュアな手段に切り替える必要があります。

本番環境では管理画面を非公開に:
本番運用時には、CA 管理画面をインターネット上に公開せず、専用の VPN 内部や CLI ツールに置き換える、または厳重にアクセス制御した環境でのみ利用するようにしてください。

まとめると、client_cert_ui() は開発時の検証用としては有用ですが、本番運用では、リスクを回避するために管理操作は専用の内部ネットワーク経由または CLI で行うのが望ましいということになります。


# 保存先DB,S3
各コード内で使用される保存先は、環境変数で指定されるか、デフォルト値が使われます。具体的には以下の通りです。

クライアント証明書発行モジュール（グループ1）
S3:
バケット名: 環境変数 S3_BUCKET の値。デフォルトは "my-client-cert-bucket" です。
リージョン: 環境変数 AWS_REGION の値。デフォルトは "us-east-1" です。
DynamoDB:
テーブル名: 環境変数 DYNAMODB_TABLE の値。デフォルトは "ClientCertificates" です。
ローカル保存:
メタデータは D:\city_chain_project\login\login_data\user_id_metadata\ に保存されます。
証明書本体（JSON形式）は D:\city_chain_project\login\login_data\user_client_cert\ に保存されます。
CA管理システム（グループ2）
S3:
バケット名: 環境変数 S3_BUCKET の値。CA管理用の場合、デフォルトは "my-ca-bucket" に設定されている例もあります（CA/config.py で設定可能）。
リージョン: 同じく環境変数 AWS_REGION の値で、デフォルトは "us-east-1" です。
DynamoDB:
テーブル名: 環境変数 DYNAMODB_TABLE の値。CA管理用の場合、デフォルトは "CACertificates" に設定されています（CA/config.py で設定）。
ローカル保存:
証明書本体は D:\city_chain_project\CA\certs\ に保存されます。
メタデータは D:\city_chain_project\CA\metadata\ に保存されます。
これにより、開発時はローカルディレクトリ、S3、および DynamoDB それぞれに証明書発行情報が保存され、後続の操作（ダウンロード、失効、一覧表示など）が行えるようになります。


# テスト実行時の作業ディレクトリを変更する
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


#　dilithium5.generate_keypair() を先に作成しておいてからテストする必要がある
【先に実行版】CA/init_ca_keys.py 
// CA/init_ca_keys.py

import os
import json
import sys

// dilithium-py を使う
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
import app_dilithium  # ←あなたのdilithiumラッパー

// 保存先パス
KEY_DIR = "CA/keys"
os.makedirs(KEY_DIR, exist_ok=True)

// Dilithium鍵生成
public_key, private_key = app_dilithium.create_keypair()

// リストなら bytes に変換してから hex化する
def to_hex(data):
    if isinstance(data, list):
        return bytes(data).hex()
    elif isinstance(data, bytes):
        return data.hex()
    else:
        raise ValueError("Unexpected key type")

// 保存内容
ca_key_data = {
    "private_key": to_hex(private_key),
    "public_key": to_hex(public_key),
    "issuer": "ExampleCA",
    "created_at": "2025-04-24"
}

// 保存ファイル
output_path = os.path.join(KEY_DIR, "ca_private.json")
with open(output_path, "w") as f:
    json.dump(ca_key_data, f, indent=4)

print(f"✅ CA鍵を保存しました: {output_path}")
これで、正しいDilithium用のca_private.jsonが作れます！！
ファイル中身は、16進文字列になります。


#　dilithium5 を埋め込んだので、python312でのサーバー起動は下記から
python D:\city_chain_project\CA\serve_ca.py
python D:\city_chain_project\CA\test_ca.py

# テスト結果
PS D:\city_chain_project> python -m CA.test_ca
D:\Python\Python314\Lib\site-packages\botocore\auth.py:425: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  datetime_now = datetime.datetime.utcnow()
D:\city_chain_project\CA\cert_issuer.py:42: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  valid_from = datetime.utcnow()
D:\city_chain_project\CA\app_ca.py:50: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
D:\city_chain_project\CA\app_ca.py:67: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "issued_at": datetime.utcnow().isoformat() + "Z"
..D:\city_chain_project\CA\ca_manager.py:28: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  revoked_at = datetime.utcnow().isoformat() + "Z"
.
----------------------------------------------------------------------
Ran 3 tests in 16.083s

OK
PS D:\city_chain_project> 


# http://127.0.0.1:6001/client_cert_ui にて開発用の画面が見れる
CA 管理画面
この画面は開発用です。証明書の一覧や状態確認、失効操作などを行います。

証明書一覧を更新
UUID	発行日時	有効期限	状態	操作
ca-test-uuid-002	2025-03-22T09:03:52.838041Z	2026-03-22T09:03:52.410615Z	失効済み	失効 ダウンロード


# 本番の CA サービスとして他社に提供するには、以下の“システム／運用”レベルの強化が不可欠です
項目;	  PoC レベル（現状）;	  本番サービス水準に必要な対応
証明書フォーマット;	 JSON + Base64 のカスタム構造;	X.509 v3 DER/PEM フォーマット、OID（ポスト量子用 OID）を正しく埋め込む
署名プロセス;	  CA秘密鍵で NTRU 暗号化による「模擬署名」;	  Dilithium を使った真正な CMS/PKCS#7 署名、証明書署名アルゴリズム（sigAlg）指定
鍵管理;	ファイルベース;	  HSM（Hardware Security Module）による鍵生成＆保護、アクセス制御
証明書失効管理;	なし;	  CRL/OCSP による即時失効通知、OCSP ステープル、証明書透明性ログ（CT Logs）
監査・コンプライアンス;	  ローカルログのみ;	  RFC 5280 準拠の監査ログ、外部監査、WebTrust/ETSI などの認証取得
運用手順／ポリシー;	  ハードコード;  	CP/CPS（Certificate Policy/Practice Statement）文書化
インターオペラビリティ;	  独自;    API	ACME や EST などおよび既存 PKI/LDAP 連携、既存 TLS ライブラリ対応


# X.509/PEM＋OID対応	
✋ 後回しでいい	要件次第で別プロジェクト化　というが、これはどういう処理なの？解説して

ChatGPT said:
“X.509/PEM＋OID対応”というのは、いわゆる「本格的な証明書運用」のための機能を指しています。大まかに言うと、以下のような処理項目です。

X.509 フォーマットのサポート
現状はおそらくJSONで証明書内容をやり取りしていますが、実運用では業界標準の X.509 証明書（ASN.1→DER）を使います。
X.509 は“Subject”“Issuer”“有効期限”“シリアル番号”“拡張領域”などを定義した仕様です。

PEM エンコーディング
DER（二進数）のバイナリ証明書を Base64 に変換し、
-----BEGIN CERTIFICATE-----
（Base64データ）
-----END CERTIFICATE-----
といった“PEM”フォーマットで配布します。多くのツール（OpenSSL、ブラウザ、OS）がPEMを前提に扱うので、PEM出力は必須です。

OID（Object Identifier）の取り扱い
X.509証明書の拡張領域（extensions）やカスタム属性はすべてOIDで識別します。
たとえば「組織名(2.5.4.10)」「メールアドレス(1.2.840.113549.1.9.1)」のように、属性ごとにOIDを振り分けてDER構造に埋め込みます。さらに、独自のメタデータを証明書に持たせたい場合は、自分でOIDを登録（またはテスト用にプライベートOIDを割り振り）して拡張領域に載せます。

ライブラリ／ツールの統合
Pythonなら cryptography ライブラリや OpenSSL CLI を呼び出して X.509/PEM の生成・検証を行うのが定石です。
いまのシンプルなJSON＋手作り署名ではなく、ASN.1→DER→PEM のパイプラインを組む必要があります。

具体的に「後回しにできる」／「別プロジェクト化できる」理由
・初期フェーズ
まずは機能検証やプロトタイプとして、JSONベースで証明書メタデータを扱い、内部的な“擬似署名”で動かす。
テストもJSON→Base64→パースという簡易的な流れで済む。

・本番フェーズ
セキュリティ要件や既存システム連携の要件が出てきたら、X.509/PEM＋OID対応を行う。
それを行うためのコードは大規模になりがち（ASN.1のスキーマ定義、各種拡張サポート、証明書失効リスト対応など）。
したがって別リポジトリやモジュールとして切り出して保守したほうが効率的、という判断が多いからです。

まとめると：
X.509 → 「本格的な証明書仕様そのまま」
PEM → Base64＋ヘッダ/フッタのテキスト形式
OID → 証明書の属性や拡張を識別する一意の番号

これらをあとから本番品質でサポートするには、ASN.1/DER→PEMのエンコーディング・デコーディングや、OIDを使った拡張領域の構築・解析のためのライブラリ統合が必要になる、ということですね。要件が固まり次第、別プロジェクトやサブモジュールとして実装を進めるのが一般的です。

✅あなたのやりたいこと（まとめ）

項目	内容	コメント
1.	独自のCAサーバーを作る	はい、その通り。あなた自身がルートCAになる
2.	独自のクライアント証明書を発行する	はい、その通り。自分のCAで署名して発行
3.	証明書形式はPEMにする	はい、必須。携帯端末でもPEM形式が標準
4.	証明書の公開鍵部分はNTRU暗号を使う	はい、ここ重要！RSA/ECDSAではなくNTRUを組み込む
5.	証明書の署名はdilithium5で行う	はい、これも超大事！量子耐性のある署名を使う
6.	将来的にはCA業務を外部委託できるようにする	はい、そのために標準的なX.509/PEM構造にしておく必要がある
7.	クライアント証明書を端末（スマホ）に保存する	はい、そのためにPEM化しておく必要がある
8.	通信時に端末側でさらにdilithium署名を付加する

🔥具体的にはこう整理して提案する！

スクリプト内容	追加する場所	理由
CAが「CA証明書（自己署名）」を作成する	D:\city_chain_project\CA\ に入れる	これは「認証局」が管理するべきだから
CAが「クライアント証明書」を発行するスクリプト	同じく D:\city_chain_project\CA\ に入れる	クライアント証明書を発行するのもCAの仕事だから
クライアント側で「クライアント証明書を受け取って保存する処理」	D:\city_chain_project\login\auth_py\client_cert\ に入れる	クライアント証明書はクライアント側で管理するべきだから
クライアント証明書を使った認証の仕組み	すでにあるD:\city_chain_project\login\auth_py\に追加・改良する	認証処理の中で証明書検証をやるから
証明書登録時（ユーザー登録時）にクライアント証明書をセットする処理	D:\city_chain_project\login\registration\に追加	新規登録時にクライアント証明書もセットしたい場合


✅つまり、新しく作る「ファイル」は
あなたのいまのフォルダ構成を尊重して、

必要な場所にだけ新しいスクリプトファイルを追加するスタイル！

無理に新しいフォルダを作ったり、全体構成を壊したりしないです。

📂イメージ例（ファイル追加例）

パス	ファイル名（仮）	内容
D:\city_chain_project\CA\	ca_generate_cert.py	CA証明書（自己署名）を作る
D:\city_chain_project\CA\	ca_issue_client_cert.py	クライアント証明書を発行する
D:\city_chain_project\login\auth_py\client_cert\	client_cert_handler.py	クライアント証明書を保存・管理する
D:\city_chain_project\login\auth_py\	auth_with_cert.py	クライアント証明書を使った認証
D:\city_chain_project\login\registration\	register_with_cert.py	登録時に証明書も登録する


# 追加ファイルだけ で X.509/PEM フローを実現します
こうしておけば、
旧 JSON ベース と 新 X.509 ベース の処理系を 段階的に切り替え られるから、
動作確認・移行テストも安全にできます。

使い方ざっくりフロー
(.venv312) $ python CA/ca_generate_cert.py          # ← ルート CA PEM と秘密鍵を作成
(.venv312) $ python CA/ca_issue_client_cert.py      # ← クライアント PEM を発行
生成された PEM を

スマホ端末側にインポート

Flask 側 API で配布／検証
……という順に拡張していけば、あなたが思い描く PQC 対応 CA / クライアント証明書基盤 がそのまま構築できます！


# フェーズ	やること	具体内容
A. SPKIを作る	NTRU公開鍵を 「SubjectPublicKeyInfo」 構造に載せる	
 ① AlgorithmIdentifier に NTRU 用の OID を入れる
 ② BIT STRING に NTRU 公開鍵バイト列をそのまま入れる
B. TBSCertificateを作る	X.509 の本体（署名前）を ASN.1 で組む	asn1crypto.x509.TbsCertificate を手構築
C. 署名する	TBSCertificate DER に Dilithium5 で署名	dilithium_app.sign_message(tbs_der, dil_priv)
D. Certificateを完成	TBSCertificate + AlgorithmIdentifier + Signature	署名アルゴリズムは Dilithium OID を使う
E. PEM化	DER を Base64 + header/footer	-----BEGIN CERTIFICATE----- …

 前提：CA証明書（PEM形式）の中身と構造
CA（認証局）のPEMファイルには、証明書情報（X.509形式）がテキスト形式で保存されています。中身は次のような構造になっています：

-----BEGIN CERTIFICATE-----
（Base64エンコードされたX.509証明書）
-----END CERTIFICATE-----
このBase64部分をデコードすると、中身は以下のようなバイナリ形式のX.509構造です：

markdown
Copy
Edit
Certificate
 └── TBSCertificate
     ├── subjectPublicKeyInfo（SPKI）←ここに「公開鍵」が入っている！
     ├── extensions（拡張領域）←オプションで追加情報を入れられる！
     └── その他の署名アルゴリズム、有効期間、発行者など

SPKIは、公開鍵に関する情報を含む領域で、以下のような構造です：
SPKI:
 ├── AlgorithmIdentifier（鍵の種類を識別、例：RSA、ECDSA、NTRU など）
 └── SubjectPublicKey（実際の公開鍵データ）
つまり、1つの証明書には原則1つのSPKIしかありません。
**1証明書 = 1公開鍵（アルゴリズム）**という制限です。


じゃあ、どこに2つ入れるのか？
証明書のこの部分：

python
Copy
Edit
spki = rfc5280.SubjectPublicKeyInfo()
この spki はこういう構造になっています：
SubjectPublicKeyInfo  ::=  SEQUENCE  {
    algorithm            AlgorithmIdentifier,
    subjectPublicKey     BIT STRING
}
それぞれ：

algorithm → 鍵の種類（例：RSAとかNTRUとか）
subjectPublicKey → 公開鍵本体（バイト列）
parameters → 実はここに「追加データ」も入れられる（今回使う場所）

🧠どうやって「2つの鍵」を入れるの？
🎯答え：
subjectPublicKey に：NTRU 公開鍵
algorithm.parameters に：Dilithium 公開鍵

👇コードで見るとこうなります
spki = rfc5280.SubjectPublicKeyInfo()
spki['algorithm']['algorithm'] = OID_NTRU_ALG

# ✅ここに入るのがメインの公開鍵（今回は NTRU）
spki['subjectPublicKey'] = univ.BitString.fromOctetString(ntru_pub)

# ✅ここに入れるのが「追加の情報」（今回は Dilithium 公開鍵）
spki['algorithm']['parameters'] = univ.OctetString(dil_pub)


❓これって正しいの？
技術的にはOKです。というのも、X.509証明書の仕様では AlgorithmIdentifier に含まれる parameters フィールドは「任意（optional）」で、しかも ANY 型なので、バイナリ形式のデータを自由に入れることができます。

つまり、誰が決めた標準に従う必要がない内部システムであれば：

✅ 自由に意味を決めて使ってよい
というのが今回の前提です。

🧪じゃあどうやって取り出すの？
証明書を読むときには：
ntru_pub = cert['tbsCertificate']['subjectPublicKeyInfo']['subjectPublicKey'].asOctets()
dil_pub  = cert['tbsCertificate']['subjectPublicKeyInfo']['algorithm']['parameters'].asOctets()
このようにして、2つの鍵を取り出せます！


# PEMに拡張が付いているかのテスト
CA/test_ca_extension.py を新規作成
CA/certs フォルダに生成済みの ca_root_*.pem を置いて
pytest CA/test_ca_extension.py を実行

これでまず「CA の PEM に拡張が本当に乗っているか」だけを確認できます。もしここが通れば、次はクライアント証明書のテストロジックに戻りましょう。

# pyasn1のテスト　（test_pyasn1.py）
まずテスト用PEMを作成してローカルのpyasn1-masterを動かす。
pyasn1-master/pyasn1/codec/ber/decoder.py　にprint文（1750行目あたり）を埋め込んでいる
これを出力させるためのテストです。

cd D:\city_chain_project\openssl-src-rs\OpenSSL-Win64\bin
.\openssl.exe version

このように表示されれば成功：
OpenSSL 1.1.1u  30 May 2023

ステップ2：自己署名証明書を作成する
同じディレクトリで以下のコマンドを実行してください：
.\openssl.exe req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 1 -nodes -subj "/CN=T

✅ ステップ3：cert.pem をテストフォルダにコピー
たとえば：
D:\city_chain_project\CA\client_certs\client_demo_test.pem

✅ ステップ4：テストスクリプト実行
先ほどの test_pyasn1.py を実行すれば、
decoder.py に埋め込んだ print() がすべて表示されるはずです。

なお、ちゃんとdilithiumが付いていることを下記で確認済み。
(.venv312) D:\city_chain_project\CA>openssl x509 -in D:\city_chain_project\CA\client_certs\client_demo_1f98bc2509db41339d45cee414506076.pem -inform pem -noout -text
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number:
            81:7d:90:3d:bc:f3:44:54:9c:ba:d1:19:db:8c:39:f0
        Signature Algorithm: 1.3.6.1.4.1.99999.1.100
        Issuer: CN = MyProductionCA
        Validity
            Not Before: May  1 20:26:11 2025 GMT
            Not After : May  1 20:26:11 2026 GMT
        Subject: CN = demo-client-01
        Subject Public Key Info:
            Public Key Algorithm: 1.3.6.1.4.1.99999.1.0
            Unable to load Public Key
AC1D0000:error:03000072:digital envelope routines:X509_PUBKEY_get0:decode error:crypto\x509\x_pubkey.c:458:
AC1D0000:error:03000072:digital envelope routines:X509_PUBKEY_get0:decode error:crypto\x509\x_pubkey.c:458:
    Signature Algorithm: 1.3.6.1.4.1.99999.1.100
    Signature Value:
        bb:33:ab:b5:e0:c0:dc:14:37:3e:c5:e4:bb:c8:e8:35:33:95:
        6f:f3:12:c9:54:62:77:b1:b9:99:45:99:91:4b:c4:1e:a7:86:
        83:27:28:49:3b:ab:d4:2d:b6:14:8a:0f:6c:22:b0:55:c3:ef:
        98:2c:1f:a2:2a:87:c8:46:17:61:a2:23:53:3a:24:85:aa:4c:
        ee:9b:dd:fd:ee:d4:21:d4:9a:4a:3c:cf:cd:57:50:3e:ed:af:
        11:67:26:1e:1e:b0:a7:f0:dd:68:91:1b:76:d5:74:ea:8f:44:
        3b:ad:33:6f:7d:df:bd:6d:79:b7:dc:1a:bd:6c:36:1b:71:30:
        31:ce:a7:5a:b5:d6:06:5e:fe:94:6b:a3:1e:f2:18:f2:0d:30:
        bd:24:ac:8c:b6:e2:3e:b0:73:21:29:b2:29:a9:c7:00:19:dd:
        a7:4b:2e:4d:e8:3a:52:00:43:82:23:7a:31:ef:78:86:9c:85:
        6f:3d:b4:ee:79:f8:dd:99:06:4f:3a:72:ed:cc:d4:c4:96:80:
        13:a9:0d:da:95:e1:d9:52:63:b9:45:a7:46:b3:6c:08:b3:be:
        8f:d2:f9:e2:86:02:20:7f:b0:53:5f:3f:3f:3e:e1:73:1b:49:
        bc:12:84:be:72:01:0b:42:0c:0e:9e:37:6d:18:49:14:1e:cf:
        76:ff:b5:dd:7e:ad:1a:af:bf:43:27:8e:9c:24:d3:2d:b5:34:
        ab:c9:ec:9c:98:a3:70:77:70:d5:09:04:07:ca:49:5d:f7:43:
        c7:36:c7:68:ed:aa:30:0e:06:5d:03:29:be:4f:89:db:43:30:
        db:aa:2e:64:4b:8b:a7:63:1c:fd:03:42:ab:28:d3:35:cd:6a:
        b6:e6:17:cd:f4:08:ba:4e:e2:e8:2e:51:ef:14:8d:41:83:c9:
        89:94:2f:f7:fb:b5:85:de:41:da:c3:93:d7:59:f8:22:27:dc:
        71:9c:b2:3a:84:ea:01:61:95:ee:5f:02:47:55:af:47:79:47:
        1a:5d:cc:cd:cc:63:7b:aa:f1:bd:84:f7:d1:71:ad:90:35:c7:
        98:aa:f3:a6:65:64:01:46:88:34:4b:f8:c4:4b:af:87:ab:01:
        13:24:52:d1:2d:d3:61:07:9c:b1:47:e6:1e:d3:47:11:55:64:
        d2:2f:f7:d2:fa:1c:ed:b8:82:c2:4f:3b:7e:26:79:c8:39:17:
        93:f4:26:43:54:6e:c2:52:9a:46:66:13:b3:c0:fb:df:7e:e9:
        2e:c9:38:a6:5a:55:a5:8d:4c:87:38:0e:8b:d9:49:4d:96:7c:
        da:d7:f0:92:7e:99:09:16:8f:63:ee:7d:2a:66:23:9c:22:11:
        5a:16:6b:d2:4f:8b:d6:aa:af:e4:02:da:b4:93:77:02:88:50:
        a0:ac:32:8f:02:d4:9d:26:ef:e1:a8:1e:6d:7a:17:52:da:17:
        18:6e:bb:e0:5c:c8:9d:7a:88:18:3a:80:33:95:5f:af:fa:9e:
        01:1c:7b:60:6c:74:29:ba:c2:be:eb:f7:fd:d7:34:f2:b1:4c:
        fe:57:06:5d:b2:7f:51:0c:93:5a:c7:f0:d3:66:de:8d:ea:ca:
        80:05:33:61:bd:64:80:4d:e8:64:81:73:cf:b1:1d:29:69:78:
        23:41:0b:bf:ae:6a:5a:1a:3c:dd:fb:73:ce:a8:0c:0b:93:9a:
        e1:8d:29:a5:a6:a1:f0:bf:b9:93:9c:15:be:ea:06:94:f8:80:
        06:dd:c7:58:af:fb:0c:63:84:bc:c3:42:6b:85:b2:ed:cf:91:
        9f:f1:4e:56:8b:b8:65:ab:a1:9d:dc:94:f5:23:8f:42:75:36:
        dd:83:0d:44:20:b3:0d:ab:0d:fc:6b:40:f0:a9:29:a0:aa:73:
        b5:c2:26:e6:a9:fd:cf:0a:ef:7a:be:f5:e3:ad:29:72:a7:a1:
        75:8b:42:6c:e0:fd:bf:ed:3b:a6:69:b2:76:e2:a2:f7:37:d5:
        e2:29:00:2a:44:a1:ac:0b:fb:44:4a:33:2d:5e:32:cb:d7:65:
        46:d4:62:91:05:6e:e5:4b:45:65:72:e6:50:7b:c3:d2:e5:26:
        ac:35:56:be:51:5b:bd:83:da:cf:65:2b:f0:84:99:a6:d7:76:
        81:af:50:f2:44:81:ae:f4:e1:6e:58:a5:c4:a5:bd:a2:af:48:
        69:07:50:33:b3:5a:0e:57:6d:7d:4c:41:34:7d:76:6a:c0:c9:
        36:44:75:4c:46:77:a4:99:51:1d:f8:73:e5:64:c0:65:23:86:
        b9:c8:ab:28:52:58:cc:01:c3:83:18:36:54:1f:b2:b1:de:81:
        29:26:c9:14:08:f8:9e:62:88:74:5c:f4:ff:b4:6c:77:05:7f:
        04:55:e8:b2:f7:16:f8:d0:bf:9a:b3:00:25:53:ad:d4:37:39:
        3e:05:4b:a7:35:11:e5:d0:55:46:87:d2:a4:d7:66:45:f0:6f:
        2e:a7:b1:2a:61:aa:c5:a7:43:e8:cc:79:d3:4e:5a:34:30:c1:
        10:3f:76:62:f5:24:99:39:24:79:00:ed:a6:15:df:02:b9:0d:
        8e:0f:c4:45:83:41:39:96:fe:3b:a2:bc:07:6b:5e:d5:0a:b8:
        f7:9c:d4:b3:26:a0:d3:88:55:95:da:cf:6e:ba:40:be:9d:b6:
        82:0d:56:82:d0:54:d1:2a:9c:78:40:e2:db:95:ca:0c:ef:f0:
        32:99:06:e4:b4:e8:32:72:b3:90:34:e3:39:4a:75:54:36:38:
        b1:c8:c8:cc:5d:2d:8a:97:28:9b:3e:9b:a2:91:42:48:cc:68:
        78:3d:e5:75:60:f9:38:34:60:91:93:be:61:de:34:6f:d4:93:
        e8:6b:4a:7b:2b:81:95:4f:98:6d:f1:0a:2e:77:7a:36:35:6d:
        bb:c0:15:66:2b:b9:9a:f4:a1:cc:d7:99:bf:89:59:85:3f:6d:
        33:b9:2f:01:f4:15:40:fb:35:65:51:ea:71:b1:fe:4a:1c:37:
        25:e1:81:c0:47:f9:44:86:da:26:9a:08:ca:c4:f3:79:f7:0b:
        99:25:09:64:1f:1b:71:b6:8b:12:07:71:4d:59:9f:44:61:3d:
        22:e0:69:00:9e:a1:e5:3f:29:4e:03:8f:0f:61:aa:05:5a:1d:
        50:f8:62:d8:d8:94:0d:12:66:0b:7c:e3:00:d1:e9:43:cd:3d:
        8d:bb:5a:31:50:b9:31:3e:0e:bb:91:ba:a0:79:ea:6a:5b:a6:
        58:99:9e:c9:1f:4e:67:84:04:05:d0:8d:c8:2d:2f:70:db:12:
        5b:4f:e5:73:61:f1:c7:ea:e3:6d:5c:c2:00:fd:29:2c:17:09:
        54:ca:32:8a:b8:2a:06:74:1f:93:84:8a:4e:39:d4:eb:7d:dc:
        e8:c0:79:95:c0:76:83:a3:d9:81:fc:35:92:61:f5:dc:2d:cb:
        4a:87:79:1a:cd:09:4f:aa:5f:a1:9e:13:23:a6:33:1b:04:e3:
        00:d1:9c:c8:ae:1d:8a:29:c8:40:fa:cb:8b:ee:be:1f:ea:d2:
        c5:d1:e6:bb:d2:e4:1b:bb:d0:68:6c:21:22:32:0b:b1:f2:79:
        5a:25:e7:1e:47:3a:65:5b:25:e5:6e:6d:a6:b5:ad:7a:a4:8a:
        d9:ae:6b:24:fa:59:f9:35:0e:dd:99:69:ed:10:93:15:61:3e:
        e9:35:8e:c3:ea:88:2d:c2:8c:92:fb:a1:5d:1a:b4:51:13:c3:
        3e:14:92:6d:f7:6f:80:79:d1:30:8d:9c:16:f6:6d:52:11:a6:
        23:4a:d0:9d:98:02:44:fc:9a:ae:3c:97:1c:33:eb:52:07:25:
        83:d1:f5:2a:3b:9a:e3:51:34:64:24:1e:fb:3f:10:1a:bc:61:
        f0:8b:7b:ef:53:c2:da:21:7f:5a:c8:26:d6:2d:84:21:88:40:
        e9:36:8f:97:31:89:1d:ad:7a:e9:61:9d:8a:3f:ed:40:01:ea:
        d3:e9:6f:9d:eb:3a:b7:59:4d:e1:2a:31:ac:14:d9:8f:43:a8:
        a5:28:78:2b:35:07:1c:2f:5c:af:d6:ab:7d:48:7b:e1:d5:e1:
        8c:7a:c2:3e:5f:00:3a:8e:1c:52:cd:80:15:b1:77:c6:67:0d:
        f4:af:f4:53:a6:cf:0e:db:bf:01:90:49:5d:a6:a5:8a:48:bd:
        90:fe:59:a2:0f:bb:19:f6:7f:b9:42:e6:14:c2:9c:16:bb:16:
        9f:f0:21:73:5f:b3:4a:96:d2:4e:32:4f:3e:51:65:c3:29:24:
        45:2c:db:7f:b5:8d:90:89:1b:91:39:51:de:80:5c:6e:3a:3e:
        1b:7d:87:f1:f6:17:09:c6:10:ff:dc:d5:da:1f:6a:9c:a5:d0:
        f5:84:8d:92:ae:f6:b2:b1:84:bf:df:0a:7a:65:66:d7:e4:cc:
        16:6d:28:75:21:1e:38:ea:77:71:19:f7:e8:91:c3:98:07:87:
        4d:3a:b2:d9:4f:2b:1b:5e:1c:a6:d0:72:36:5e:de:7e:d8:5b:
        46:ca:db:f7:e9:c5:94:b8:f0:36:a5:73:d3:b1:9c:0a:f1:ce:
        f1:66:36:95:4b:06:36:8f:f5:2b:82:d1:d2:58:5b:40:59:f5:
        05:45:a9:e3:49:1b:1a:7c:65:20:28:c8:3a:a2:f1:5f:13:85:
        c8:e5:b8:5d:f8:40:59:00:9d:93:88:7e:8e:85:1a:b1:b5:16:
        d6:70:b0:6a:36:98:17:77:cd:c0:71:65:59:ee:98:a9:09:8c:
        20:a7:81:df:24:82:ce:70:1e:af:da:ba:b6:41:66:7e:aa:be:
        1d:d2:db:b5:60:9c:f7:06:ff:a7:ef:37:c4:37:1e:4b:12:77:
        4d:44:0d:13:bc:a0:07:29:35:5f:fe:2b:e2:5b:7a:c2:80:2e:
        6e:82:7e:fc:08:ad:5a:c2:87:b1:86:f1:5e:5d:d3:d7:75:61:
        58:ac:80:48:b5:8a:41:1b:a7:9a:ba:36:7f:f1:a4:fd:3d:55:
        78:55:aa:59:ec:d0:e2:c1:e3:01:eb:e8:32:dc:d7:af:3e:e3:
        69:51:f8:4f:43:9a:db:72:95:98:6e:6f:73:2b:7e:7f:65:f9:
        17:35:73:62:f5:63:1d:3e:1a:30:4c:8d:3b:96:43:2d:e3:d5:
        c3:cd:62:94:05:7d:95:5c:4e:19:77:72:ac:33:f2:fc:36:2d:
        bc:2b:51:c0:cc:d7:16:af:3f:d6:67:ca:2c:90:78:7c:7d:b2:
        3f:e4:53:95:e6:84:dd:57:a5:5c:fa:12:0d:7d:3f:0e:da:d7:
        b0:45:7f:e2:ad:14:33:3d:df:92:97:f4:f9:03:71:35:ed:29:
        42:d2:9c:85:c2:38:37:c9:01:02:76:83:16:ac:52:c7:d4:9a:
        0e:95:8e:10:0f:0c:4a:10:6e:06:e5:8b:3f:9b:39:b9:d2:aa:
        ca:b2:ae:48:86:9f:70:36:8b:ec:45:d1:a0:e9:eb:ec:84:9c:
        07:1d:b2:10:2e:4c:e7:90:b9:08:17:25:7a:b0:1f:c4:cd:2e:
        d2:0d:f3:2a:78:c6:6a:58:7c:26:a5:bc:3f:6d:c3:f7:1f:e3:
        26:6b:e2:06:28:8a:b9:e7:f3:68:9d:4b:6b:bd:16:9a:d3:b7:
        da:cd:d1:7b:6e:d2:fb:82:85:d9:6e:0c:98:f6:1d:7e:74:61:
        ab:f9:62:47:4f:98:2b:9c:9f:49:fb:53:6f:a5:d4:a2:8a:5c:
        bb:cb:6f:8b:19:b3:63:bf:8b:4c:11:15:94:22:bc:cd:d0:bd:
        6d:61:34:32:49:e0:5e:82:12:e2:59:f2:3b:4d:62:96:8c:ab:
        6d:6b:8a:bd:cd:3e:99:d4:24:bb:0a:43:eb:ad:d8:54:3f:85:
        6d:d6:27:3d:8b:35:1c:65:c4:5e:0e:d8:a8:46:90:c9:99:50:
        02:c6:06:fb:d1:73:bc:78:31:72:51:d8:0e:19:8e:34:41:42:
        99:09:e6:36:a4:db:d9:c3:a4:e9:4c:c4:7e:45:9b:d6:f3:5b:
        ff:10:22:ad:07:d2:19:b4:d5:62:5e:8f:d7:e1:4f:93:ff:e9:
        e0:ab:e9:85:23:eb:e3:c8:c4:14:0d:ad:ee:00:1b:b9:4f:e1:
        d6:55:dc:ee:57:9b:65:01:f6:f7:37:6c:bd:1d:ea:53:85:9e:
        54:ff:c2:eb:a1:dc:18:de:6a:25:5a:bf:7f:a8:9c:28:d6:b6:
        72:02:fb:ee:9c:69:36:c3:c1:d1:2c:d2:6a:e5:be:92:8e:10:
        f2:25:c2:a6:3b:4c:09:20:dd:ac:60:71:9d:9d:ea:58:0d:dc:
        06:ce:b6:a9:46:76:37:64:2d:7b:9d:d5:79:a5:8a:ea:d7:6e:
        79:e3:e9:51:61:d7:af:22:12:8a:a4:23:6e:d0:7f:ff:79:bd:
        1f:48:9c:f4:f8:86:00:b8:5d:da:91:3c:03:70:1e:42:fe:76:
        39:20:72:d0:cc:09:f5:58:1f:db:9e:19:5e:02:bd:2f:4a:c4:
        75:8c:76:1f:8f:42:d6:4a:b0:28:a4:22:ef:4e:e1:a3:26:15:
        7e:77:e2:e0:79:27:09:56:b0:b0:24:1e:a7:50:09:ed:6a:6f:
        64:84:fd:82:34:3f:72:39:0e:50:4b:57:dd:4d:cb:69:f6:33:
        e5:29:e2:6e:f4:e9:cc:52:32:f7:a3:f7:b9:80:06:8e:c4:cb:
        28:a6:f1:0d:47:a4:fc:6a:4e:32:49:44:cc:c5:93:eb:95:ed:
        3f:4f:e6:1e:a4:82:4a:8f:d9:9a:07:2f:06:48:fb:cf:76:ee:
        ec:d5:5f:ea:ee:77:c6:a0:cf:f9:ac:3b:ad:b0:eb:27:6a:06:
        a3:e5:eb:f9:1c:59:e3:56:71:a3:87:0c:f0:f7:af:fc:e0:4e:
        72:cb:2f:15:8e:c4:9f:e3:b3:6d:98:42:f1:54:2d:8a:dc:e7:
        6a:f7:30:1c:a6:cd:99:64:5f:b0:e8:46:c0:6e:3a:c5:7e:3a:
        fe:be:3f:ba:7e:ab:56:03:e5:52:b1:d4:f2:92:88:33:e5:e6:
        09:4e:9a:2e:cb:b3:4f:ff:04:ce:6d:09:0e:49:2f:ad:6d:2c:
        0e:a7:50:96:a3:50:3e:9c:5f:b1:8b:84:18:8a:f1:63:8d:7f:
        62:50:e5:bb:fc:5d:88:f6:62:40:18:5b:dc:7a:05:ee:a4:f2:
        e6:c5:90:23:ef:7b:f7:a1:34:c3:2b:7a:9b:5e:f3:83:cf:5c:
        00:a2:67:e5:7a:9a:2c:b6:24:a0:71:9b:a2:45:4f:ef:2a:c2:
        1c:c7:ab:d9:85:b2:cd:c4:af:cf:ae:65:da:6f:e3:74:30:69:
        ce:41:af:f4:ef:35:17:cb:f6:a7:f2:59:b9:9a:bb:40:8b:41:
        c4:a3:f3:16:bb:a4:4f:4d:ae:80:f3:4a:4a:63:7f:96:fe:e9:
        cd:9d:7e:bb:fe:9b:04:37:16:4e:e3:70:de:d3:fb:05:a4:96:
        d4:fa:d0:36:40:2f:41:36:0f:c6:c3:71:d1:33:93:17:b6:a3:
        5f:37:12:e6:0f:f6:65:62:dd:5f:c5:cb:a7:56:9a:10:fa:aa:
        32:6e:2e:4c:1d:2c:fc:6f:df:9c:c4:fd:94:08:b1:8d:86:63:
        8b:2c:75:36:44:58:5d:27:ce:3c:bf:7c:71:7d:24:c7:ee:9f:
        0f:a0:d6:55:d9:2a:95:3b:35:a7:52:c7:7f:5f:ed:82:54:85:
        2c:3e:f3:ce:56:ed:04:94:d1:8a:9b:0e:7a:8e:49:90:ff:a6:
        7d:ee:5a:82:44:9a:5a:39:b7:ee:53:0a:1c:d9:f2:18:33:6e:
        17:f5:7b:3a:eb:f4:99:9e:fb:ea:e0:61:de:54:b1:40:ab:f1:
        10:df:0a:1f:51:a0:12:28:57:fa:ac:6e:31:14:02:dd:6b:41:
        40:08:3e:59:22:de:2f:4a:38:78:5f:4e:23:ea:da:fa:d2:bd:
        1a:14:a1:a6:3d:50:47:72:9a:96:24:18:95:ef:6a:2c:15:e9:
        29:89:2e:a6:b7:00:4a:61:e1:8c:40:65:83:d4:09:fb:bd:93:
        1a:ea:26:cd:19:79:8e:e5:4f:12:9a:84:d4:2c:b8:e1:ee:dd:
        41:a5:c1:12:a7:2f:66:18:e9:0f:9c:4d:6d:6c:65:ec:46:1d:
        57:d8:07:09:f7:13:34:52:88:07:2c:3a:56:d0:dc:6b:46:1f:
        65:4c:21:50:a4:0e:d3:6d:2e:45:b1:3d:bb:d9:6d:44:a5:5d:
        c0:d4:05:86:f8:a4:b8:3c:3f:cd:b1:8b:0c:17:77:62:4f:5c:
        d7:8f:06:3c:fa:ac:26:a8:f7:1f:8d:83:ab:c9:9d:cc:c8:ff:
        60:b0:b9:b3:01:78:7a:83:c6:5d:45:36:d9:60:88:f5:88:b8:
        f2:2a:01:27:9e:c4:d2:bf:9f:e6:59:82:83:fe:7d:d8:5c:e5:
        32:a4:2c:57:70:40:9b:1b:dd:16:fc:6d:c4:66:57:a9:6a:31:
        0f:dd:27:fe:4c:90:dd:0e:1b:c3:af:96:ed:52:21:a9:dc:fa:
        4d:ba:8a:a8:da:9e:ce:8f:6e:6f:b3:d3:19:04:89:6e:cb:ac:
        60:ee:07:7b:3d:0c:3e:2f:76:b1:11:68:33:66:46:2e:81:a9:
        11:48:05:34:cf:e5:65:a8:43:77:06:b7:07:b5:0a:ba:a7:ee:
        56:78:14:2e:62:da:d8:b8:5d:00:d7:dd:b6:9b:b7:3e:8a:ba:
        a3:8f:df:59:6d:a7:72:55:67:c5:c3:5e:77:68:85:91:12:8f:
        1c:c8:cf:21:07:b1:44:d0:8b:a1:9a:58:9b:c2:6e:2e:a9:24:
        4a:fb:d1:70:89:8e:b3:86:85:fd:3f:2c:23:42:5f:76:df:a6:
        08:c9:5c:93:04:20:1a:ec:b9:5f:3a:63:ce:24:29:7e:4d:34:
        7e:dc:a0:e1:b2:ff:45:95:0d:9e:c2:ce:6d:99:ca:58:47:f2:
        1b:81:d1:d2:01:85:eb:a3:b8:c7:ec:05:ef:18:a7:8c:7c:cc:
        90:97:eb:4e:c0:e8:fa:df:d4:80:fa:cf:b7:8b:3d:d3:05:39:
        6f:74:82:08:78:ed:25:06:3d:5a:95:2e:b2:ad:32:35:2f:0c:
        1e:d5:3b:a1:02:d6:d0:b1:de:22:63:c1:6a:e3:99:a4:25:5b:
        cd:fd:f0:2b:f2:bf:50:3d:35:e9:ac:56:c7:50:9f:4f:97:94:
        ae:1d:ec:65:12:6c:dc:00:83:83:07:1a:25:6e:4c:c7:2e:7f:
        6c:43:54:16:76:7e:c5:f3:ad:65:3b:08:ba:15:24:4f:4d:3f:
        72:56:97:f8:a9:3b:26:0d:1d:0e:a7:96:9e:49:35:43:5a:5c:
        2e:36:bd:b1:57:48:24:de:4b:b2:31:21:a7:54:2d:c6:d0:f8:
        86:ba:39:04:aa:13:de:82:17:c8:ab:be:bb:e8:6f:f0:8d:1a:
        9c:de:04:0b:fe:08:74:27:ce:43:bf:53:52:7e:31:17:53:af:
        8f:5c:84:78:91:83:4f:8c:bb:2c:b8:0b:90:42:f7:22:3d:24:
        4b:8a:0e:f5:e0:be:7f:f5:f6:c7:f8:b2:76:8f:6d:a2:01:5d:
        bc:b2:ac:4b:d9:d3:05:14:db:ce:bf:b6:57:6b:ae:d6:8a:c5:
        8a:18:00:0f:bf:62:84:54:0b:18:9c:95:42:c8:59:f6:98:d2:
        da:47:25:89:e9:54:22:b0:45:86:c6:b6:c9:79:03:6c:b4:55:
        35:f3:60:15:c8:e8:85:0a:a4:39:c0:04:4d:44:a2:06:74:27:
        6a:24:61:eb:3a:bd:13:9b:a7:fc:88:5a:66:24:b1:9d:91:6a:
        8b:0e:c6:ea:dd:76:9d:4d:dd:6d:71:93:e0:d1:65:36:ca:f0:
        d2:df:ce:13:e0:ac:54:1f:c6:5a:e2:7f:a8:5e:5d:d4:c0:d8:
        39:07:e4:eb:75:cc:69:91:a0:b3:89:56:f4:5f:97:ab:86:72:
        48:11:c8:a9:a2:40:9b:c6:d2:7c:a3:47:b8:a9:26:da:94:2c:
        03:c4:80:b1:c0:2c:ab:29:8b:95:b2:c6:be:90:c7:b9:f5:67:
        c8:39:ae:20:65:63:06:92:c9:7e:f1:5f:ba:fd:15:b7:0f:85:
        c9:7a:b3:80:3c:7f:af:47:19:44:77:13:43:13:4e:34:ab:87:
        58:4a:e2:66:d3:55:d1:11:1d:6a:9f:99:3d:5e:aa:42:74:e6:
        47:84:2a:cf:ae:68:f7:bd:f6:ea:28:fe:ec:24:03:45:60:54:
        28:5d:f7:6c:b3:cd:1c:58:49:54:7e:c1:5c:68:d4:97:f3:51:
        83:4c:ad:44:13:f2:0f:a8:5f:33:9c:c8:fd:55:c9:7c:36:9d:
        d4:ca:77:52:dc:f2:15:f9:2e:fd:24:07:55:f6:49:cf:07:3f:
        eb:cb:ac:1f:89:19:70:17:cd:d6:d7:19:3f:ed:b4:c5:c1:fd:
        9d:26:66:f3:a7:4d:f6:01:cc:1d:66:de:e6:27:6d:16:59:eb:
        17:e0:b7:27:f5:42:be:b2:13:86:8c:cc:f1:3e:c8:51:61:10:
        65:10:8e:d4:29:52:f5:30:67:a4:14:9d:eb:79:4e:82:0a:da:
        07:2d:97:f6:d8:9e:26:d6:45:8a:43:de:52:81:c9:7f:1e:e4:
        65:b5:a3:a3:c0:c6:58:21:a0:5a:16:1a:79:2b:bd:0c:e5:b1:
        63:4d:05:94:ca:6b:a0:04:53:11:97:79:44:cb:ac:6f:5c:4c:
        c5:71:aa:8d:b3:f1:cd:38:ef:7a:32:57:d6:48:3c:28:ef:dc:
        f2:83:a5:fc:7e:66:27:20:b5:23:86:f1:f5:72:30:a9:7a:28:
        90:65:9d:52:28:cc:d7:78:6d:00:20:f6:20:57:12:0c:72:6c:
        59:3d:4b:29:d6:8d:0d:bb:8c:13:be:9d:05:06:53:ed:4a:9d:
        eb:4d:d3:38:ab:ff:0b:2a:aa:49:a8:8b:cf:16:7e:ec:55:71:
        7d:bf:7c:4d:63:a2:f0:24:36:5f:35:1d:ea:37:d0:8b:b3:c7:
        c0:0b:ae:91:8e:e6:b2:a6:63:32:17:08:45:12:be:85:30:96:
        4c:d5:dc:ea:b6:a0:3b:6f:d4:cb:b5:39:6a:a3:8f:c1:dd:c8:
        23:8d:c0:a5:90:3a:d4:f3:e3:77:c5:62:d9:3b:2f:0d:c0:98:
        90:40:48:90:bb:ff:bf:19:17:b4:b2:26:74:02:f1:b6:6e:de:
        4f:d3:65:02:15:d5:dd:90:82:9d:7c:d2:0b:09:e8:8b:84:fe:
        19:25:00:27:2f:ff:5a:c2:ec:81:57:89:83:d7:86:e0:61:6b:
        63:f7:f0:09:61:bd:cb:4b:1c:77:96:2b:ec:97:f1:b3:92:da:
        00:ba:96:78:04:d2:1d:5a:0a:6b:ef:26:67:f4:a7:b3:e8:9a:
        e5:77:7e:75:2e:71:0c:57:52:f1:54:30:47:23:38:55:80:94:
        d1:e0:67:d7:46:92:6f:20:90:5f:b9:9b:76:cd:b8:5f:9c:bf:
        e5:eb:84:9d:0d:d8:2b:17:61:00:7c:be:70:7a:80:01:e0:72:
        cc:0b:f7:70:dc:a3:78:82:f4:4e:28:9e:13:fc:c7:85:16:8f:
        21:3d:ce:ec:13:cd:ca:7d:b1:7c:ac:11:42:00:6a:fc:19:6e:
        ee:35:d3:51:17:ca:0b:6c:1c:a9:21:d2:48:41:30:4e:d1:23:
        b7:7f:15:b7:f1:5f:d9:93:d8:84:60:7b:78:db:6c:ab:c2:b4:
        d8:86:16:d0:6e:6a:9d:62:c1:f0:fa:1a:08:70:de:73:cd:b8:
        50:6a:e5:d2:f9:f8:06:94:68:c5:95:12:f4:52:50:19:b2:d7:
        6c:68:18:ca:de:ed:24:64:14:f8:c3:e5:7b:e9:ed:bc:e7:d0:
        f5:dc:fa:bd:fc:05:7e:c5:c4:6e:c1:cc:29:10:22:81:5f:2b:
        2e:f7:25:5e:a8:57:44:c3:26:e6:8f:cf:0c:ba:d5:b6:24:01:
        6c:28:d9:70:72:11:7d:a3:69:f2:0f:73:fa:2a:3e:34:b6:6a:
        0a:ab:a5:45:78:b8:27:16:a8:d0:fa:6f:4d:22:66:9c:23:0c:
        3c:23:57:c9:4d:46:de:f1:4f:b3:1a:1f:7e:c1:65:70:a1:b8:
        8e:e9:31:eb:77:07:ef:48:17:4d:53:aa:65:b3:dd:b0:9b:09:
        0c:87:f2:08:ce:f5:46:1f:16:2d:51:06:1a:20:31:39:5d:93:
        9c:c7:17:1a:28:50:64:6b:74:89:96:a4:d7:07:32:35:64:69:
        86:91:b3:f5:09:87:bf:eb:fb:09:1d:90:ca:dc:2a:3d:7f:ca:
        d7:eb:05:19:c9:d6:e2:ee:fc:ff:00:00:00:00:00:00:00:00:
        00:00:00:00:00:00:00:00:00:00:00:03:0c:17:20:25:2a:30:
        38:30:82:03:4e:a0:03:02:01:02:02:11:00:81:7d:90:3d:bc:
        f3:44:54:9c:ba:d1:19:db:8c:39:f0:30:0c:06:0a:2b:06:01:
        04:01:86:8d:1f:01:64:30:19:31:17:30:15:06:03:55:04:03:
        0c:0e:4d:79:50:72:6f:64:75:63:74:69:6f:6e:43:41:30:1e:
        17:0d:32:35:30:35:30:31:32:30:32:36:31:31:5a:17:0d:32:
        36:30:35:30:31:32:30:32:36:31:31:5a:30:19:31:17:30:15:
        06:03:55:04:03:0c:0e:64:65:6d:6f:2d:63:6c:69:65:6e:74:
        2d:30:31:30:82:02:ce:30:0c:06:0a:2b:06:01:04:01:86:8d:
        1f:01:00:03:82:02:bc:00:73:d3:fd:5b:9c:a4:b1:d4:14:8f:
        1a:f0:38:fd:d7:f2:2f:d3:8d:95:ad:88:8e:e1:f8:9a:f7:23:
        ad:9f:59:16:92:5f:7e:21:e7:71:d1:bb:39:4d:5b:10:09:33:
        f5:60:16:c1:15:30:02:5b:b4:2a:e9:89:19:25:6d:f3:9d:ab:
        c2:4b:93:32:3f:be:53:d6:73:c4:a8:d8:11:2c:f2:55:e3:f4:
        a5:e1:26:cd:a8:dd:84:07:8c:69:51:0a:6f:77:99:09:d4:79:
        7a:90:b1:56:17:64:c9:2e:ee:0c:5f:66:04:33:72:43:42:e8:
        64:82:f1:87:a9:c2:97:b4:54:6b:70:08:46:58:75:00:1d:5a:
        53:82:be:a8:39:29:f5:51:46:d9:23:37:74:d5:a5:68:02:75:
        f5:4b:78:86:72:5c:de:11:75:7c:f9:d0:19:a9:e2:8c:4a:22:
        a3:e9:a1:bb:80:23:6c:cc:4b:55:e2:10:03:f7:2c:0a:af:1b:
        10:b9:90:d1:f3:a6:e7:82:74:66:3e:eb:d4:be:35:07:4c:d3:
        07:0c:45:ab:4d:f2:1c:bf:6b:ec:ea:75:00:8c:19:b7:36:97:
        00:56:d8:fa:15:2e:8e:27:7a:f2:f6:07:75:f5:a6:3d:38:cb:
        d7:50:22:e3:1e:6f:de:a1:e8:42:8d:6b:f8:7f:99:a1:74:a9:
        c6:a7:8f:d8:de:84:a3:a4:df:e4:15:b6:19:bc:23:3e:bc:89:
        d8:8c:58:da:e7:8f:e3:44:e7:7d:55:10:7f:a2:77:8b:27:35:
        ac:13:6a:cc:eb:68:c3:2e:82:f5:ea:9b:e3:27:3b:6f:70:83:
        55:a3:9b:98:32:0d:1a:83:80:b7:f8:96:74:c4:e8:ad:98:64:
        8e:86:87:77:99:61:e0:13:e4:4c:39:83:5e:8a:a8:7a:54:8b:
        e2:99:3f:25:8a:20:0e:4a:cc:cc:51:f0:7c:d7:ea:4a:af:d4:
        26:2c:e0:b5:2c:fc:74:21:fe:91:b2:1c:44:00:02:07:61:0b:
        7e:58:71:20:bc:79:59:98:ec:d2:09:1f:40:88:36:98:40:c4:
        69:21:e6:e1:1f:86:84:64:fa:cf:e3:1f:f8:70:c7:de:54:34:
        1e:be:68:27:62:c7:63:4d:3f:52:da:a5:57:24:22:eb:09:0e:
        8b:b1:b7:b1:33:40:1e:66:c8:fb:70:db:39:b4:cf:0e:51:91:
        52:71:e1:03:70:9d:42:02:c0:8f:94:0d:24:8f:e8:6f:20:a1:
        3b:60:f5:a8:81:36:81:b0:c7:52:35:7b:7b:4c:65:30:a1:a4:
        41:d6:de:5b:bd:d9:09:e1:6e:bc:b4:ac:72:b8:cf:1d:79:d1:
        3a:0d:00:a1:81:a8:01:8b:b3:b3:84:19:10:ab:a3:e2:b7:18:
        73:cb:54:cc:72:a7:1c:fe:16:c5:e2:c9:e8:44:fa:29:be:4c:
        37:79:0b:c0:92:98:a9:91:0f:e3:94:c4:b5:8c:2b:de:c2:9c:
        cd:37:83:8c:9f:1d:44:da:07:d7:72:03:b2:6e:4c:a7:81:2f:
        5e:fc:e8:a1:81:95:65:f7:95:38:07:ae:d0:97:d6:8e:1a:d3:
        32:b2:2b:14:c5:95:ea:fb:39:ab:86:f2:0d:b4:d3:fa:f5:31:
        de:fd:8f:d8:86:d3:c6:cf:dd:8c:0f:0a:f4:22:aa:4b:47:97:
        c4:34:08:a5:c9:83:f9:87:13:ba:d3:52:82:43:0c:9f:d2:27:
        6e:c3:5b:d0:fb:18:01:6e:50:50:ef:eb:19:af:69:05:17:a1:
        ce:78:6b:07:87:c3:bf:f1:5f:68:f5:13:dd:9a:86:f1:f6:4a:
        62:63:4a:36:0c

日本語解説
X.509 の拡張部（extensions）が空
あなたが作った証明書には拡張部を追加していないので、extensions フィールド自体が存在せず、空で返ってきます。よって従来の「extensions を探す」コードはそもそも当てはまりません。

Dilithium 公開鍵は SPKI に入っている
「Subject Public Key Info」は証明書の必須要素で、ここに公開鍵本体が BIT STRING として格納されています。カスタムアルゴリズムの OID（1.3.6.1.4.1.99999.1.0）と、生の公開鍵バイト列がこの中にあります。

.asOctets() でビット文字列からバイト列を取り出す
pyasn1 の BitString オブジェクトには .asOctets() メソッドがあり（先頭の「unused bits」バイトを内包せずに）バイト配列を取り出せます。それを .hex() で表示すれば、Dilithium 公開鍵の16進表現が得られます。

これで「拡張がない」問題は解決し、SPKI からちゃんと Dilithium 公開鍵を取り出せるはずです。

(.venv312) D:\city_chain_project\CA>python test_pyasn1.py
🔑 公開鍵アルゴリズム OID = 1.3.6.1.4.1.99999.1.0
=== Dilithium 公開鍵（hex）===
73d3fd5b9ca4b1d4148f1af038fdd7f22fd38d95ad888ee1f89af723ad9f5916925f7e21e771d1bb394d5b100933f56016c11530025bb42ae98919256df39dabc24b93323fbe53d673c4a8d8112cf255e3f4a5e126cda8dd84078c69510a6f779909d4797a90b1561764c92eee0c5f660433724342e86482f187a9c297b4546b7008465875001d5a5382bea83929f55146d9233774d5a5680275f54b7886725cde11757cf9d019a9e28c4a22a3e9a1bb80236ccc4b55e21003f72c0aaf1b10b990d1f3a6e78274663eebd4be35074cd3070c45ab4df21cbf6becea75008c19b736970056d8fa152e8e277af2f60775f5a63d38cbd75022e31e6fdea1e8428d6bf87f99a174a9c6a78fd8de84a3a4dfe415b619bc233ebc89d88c58dae78fe344e77d55107fa2778b2735ac136acceb68c32e82f5ea9be3273b6f708355a39b98320d1a8380b7f89674c4e8ad98648e8687779961e013e44c39835e8aa87a548be2993f258a200e4acccc51f07cd7ea4aafd4262ce0b52cfc7421fe91b21c44000207610b7e587120bc795998ecd2091f4088369840c46921e6e11f868464facfe31ff870c7de54341ebe682762c7634d3f52daa5572422eb090e8bb1b7b133401e66c8fb70db39b4cf0e51915271e103709d4202c08f940d248fe86f20a13b60f5a8813681b0c752357b7b4c6530a1a441d6de5bbdd909e16ebcb4ac72b8cf1d79d13a0d00a181a8018bb3b3841910aba3e2b71873cb54cc72a71cfe16c5e2c9e844fa29be4c37790bc09298a9910fe394c4b58c2bdec29ccd37838c9f1d44da07d77203b26e4ca7812f5efce8a1819565f7953807aed097d68e1ad332b22b14c595eafb39ab86f20db4d3faf531defd8fd886d3c6cfdd8c0f0af422aa4b4797c43408a5c983f98713bad35282430c9fd2276ec35bd0fb18016e5050efeb19af690517a1ce786b0787c3bff15f68f513dd9a86f1f64a62634a360c

❌ Dilithium 拡張が見つかりませんでした。