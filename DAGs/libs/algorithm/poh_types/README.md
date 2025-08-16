poh_types/                              ← リポジトリルート
├── LICENSE                             ← ライセンス（Apache-2.0 など）
├── README.md                           ← パッケージ概要・インストール手順
├── .gitignore                          ← __pycache__/、*.py[cod] など
├── pyproject.toml                      ← PEP 517/518 によるビルド設定
└── poh_types/                          ← 実際の Python モジュール
    ├── __init__.py                     ← パッケージ定義
    ├── app_types.py     　　　　　　　　←　エンドポイント
    ├── _version.py                     ← バージョン同期用
    ├── types.py                        ← PoH_TX, PoH_ACK, PoH_REQ のデータクラス定義
    ├── exceptions.py                   ← 独自例外定義 (e.g. PoHTypesError)
    └── tests/                          ← 単体テスト
        ├── __init__.py
        ├── test_cli.py
        └── test_types.py               ← dataclass のシリアライズ／検証テスト

poh_types パッケージは、“Proof of Hold”（PoH）関連のトランザクションデータ構造だけを切り出した、極めてシンプルかつ汎用的なモジュールです。以下の機能を持っています。

１．主要クラス（types.py）
PoHTx
概要
PoH トランザクションのベースクラス。
フィールド
tx_id: str — 元トランザクションの一意識別子
holder_id: str — 保持者ノードの ID（例: ノードの証明書 CN）
timestamp: float — PoH 発行時刻（UNIX 秒）

メソッド
__post_init__ — 空文字エラーや型エラーをここで検出・例外化（PoHTypesError）
to_json()／from_json() — 同期的な JSON 直列化／逆直列化
to_json_async()／from_json_async() — 非同期版（将来の I/O 拡張に備えた stub 実装）
validate_timestamp(allow_drift) — 非同期的に「現在時刻とのズレが許容範囲内か」を検証

PoHReq
PoHTx を継承した「保存依頼」トランザクション型。
現状は追加フィールド無しだが、後から属性拡張可能。

PoHAck
PoHTx に以下のフィールドを加えた「保存証明」トランザクション型。
storage_hash: str — 実データの SHA-256
sig_alg: str — 署名アルゴリズム名（例: "dilithium3"）
signature: str — base64 化済み署名文字列
__post_init__ で全３フィールドの空文字チェックを実施。

２．エラー型（exceptions.py）
PoHTypesError
データ構造の初期化やバリデーション失敗時に投げられる専用例外。
上位モジュールではこれをキャッチして適切にエラーハンドリングを行います。

３．CLI ツール（app_types.py）
このモジュールをエントリポイントにすると、

python -m poh_types.app_types req ...
→ PoHReq JSON を生成・標準出力

python -m poh_types.app_types ack ...
→ PoHAck JSON を生成・標準出力

python -m poh_types.app_types validate ...
→ PoHTx のタイムスタンプズレ検証を非同期実行し、成功なら "OK"、失敗なら "[ERROR]" を stderr に出力して非ゼロ終了

といったユーティリティ操作が可能になります。
内部では asyncio.run(...) を使って、将来的な拡張（外部 I/O など）にも対応できるよう設計しています。

４．同期／非同期対応
直列化／解析 は同期・非同期両対応メソッドを持ち、現状は同期実装のラッパーですが、非同期 I/O での拡張時にそのまま流用できます。

タイムスタンプ検証 など、将来的にネットワーク時刻取得や外部サービス照会を組み込む際にも、await tx.validate_timestamp_async() などとして使えます。

５．使いどころ
上位の poh_builder／poh_validator クレートからデータ型をインポートし、PoH リクエスト・応答を組み立てたり検証したりする際の共通スキーマ。

テストやデバッグで、まずは PoH トランザクションの形を確認したい場合の軽量ツールとして最適。

まとめ
責務を「型定義とシリアライズ・基本バリデーション」に絞る ことで、他の PoH 関連モジュールと疎結合に連携。
同期・非同期両対応インターフェースを持ち、将来の I/O 拡張や Web フレームワーク統合に備えた設計。
CLI 付きで手軽に JSON を生成／検証でき、CI テストにも組み込みやすいモジュールです。


#　wheel を dist\ に置きたいなら
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

pytest 用単体テスト。
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_types\pytest poh_types/tests

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_types>pytest poh_types/tests
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: D:\city_chain_project\DAGs\libs\algorithm\poh_types
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 10 items

poh_types\tests\test_cli.py ....                                                                                 [ 40%]
poh_types\tests\test_types.py ......                                                                             [100%]

================================================= 10 passed in 1.34s ==================================================
