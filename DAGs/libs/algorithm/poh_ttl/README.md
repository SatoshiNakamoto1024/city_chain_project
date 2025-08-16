poh_ttl/                                 ← リポジトリルート
├── LICENSE                              ← ライセンス (Apache-2.0 等)
├── README.md                            ← パッケージ概要・インストール・使い方
├── .gitignore                           ← __pycache__/、*.py[cod] など
├── pyproject.toml                       ← PEP 517/518 ビルド設定 (依存関係、パッケージ名、バージョン等)
└── poh_ttl/                             ← 実際の Python モジュール
    ├── __init__.py                      ← パッケージ定義（バージョン等）
    ├── exceptions.py                    ← 独自例外定義 (TTLManagerError)
    ├── manager.py                       ← `TTLManager` クラス (TTL スキャン＆GC)
    ├── cli.py                           ← CLI エントリポイント (`scan`／`run`)
    └── tests/                           ← 単体テスト
        ├── __init__.py
        ├── test_manager.py              ← `TTLManager.scan_once` のテスト
        └── test_cli.py                  ← CLI (`scan` コマンド) のテスト

以下、poh_ttl が提供する主な機能と内部構成を詳しく解説します。

1. 基本コンセプト
TTL（Time To Live）管理
保存済みの PoH トランザクションに「有効期限」を設定し、期限切れになったものを自動的に削除（ガベージコレクション）します。

非同期処理
Python の asyncio タスクで定期スキャンを回し、I/O 待ち中も他処理をブロックしません。

StorageManager との連携
永続化レイヤー（poh_storage.StorageManager）と組み合わせることで、ファイル＆SQLite 両方から期限切れデータをまとめて掃除します。

2. コアクラス：TTLManager（manager.py）
class TTLManager:
    def __init__(self, storage_manager: StorageManager, ttl_seconds: int):
        self.storage_manager = storage_manager
        self.ttl_seconds     = ttl_seconds
        self._task           = None
scan_once(): List[str]

storage_manager.list_txs() で全 ID を取得
各 ID のメタデータ（保存時刻）を調べ、now - timestamp > ttl_seconds なら削除
削除した ID のリストを返す
例外時は TTLManagerError にラップ信号化
run(interval_seconds: int)
バックグラウンドで定期的に scan_once() を呼び、削除結果をログ出力
asyncio.create_task で永続的に動作させる

3. CLI：poh-ttl（cli.py）
scan コマンド
poh-ttl scan --base ./data --db ./data/poh.db --ttl 3600
→ 一度だけスキャンを実行し、標準出力に Expired: [...] を表示

run コマンド
poh-ttl run --base ./data --db ./data/poh.db --ttl 3600 --interval 600
→ 指定秒間隔で GC を繰り返し、INFO: TTL GC removed: [...] をログに出力

Windows 対策
if sys.platform=="win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
で asyncio のイベントループ競合を防止

4. エラーハンドリング（exceptions.py）
TTLManagerError
スキャン中の I/O や内部エラーを包んで呼び出し元に通知できます。

5. テスト構成（tests/）
test_manager.py
TTL の境界値テスト（有効期限前／後の削除動作）

test_cli.py
サブプロセス経由で scan コマンドの出力検証

いずれも非同期リソース（StorageManager）を finally: await close() でクリーンアップし、I/O リークを防止しています。

6. 実運用イメージ
マイクロサービスとして独立動作させるなら、poh-ttl run を常駐プロセス化。
ワンオフ実行であれば定期ジョブ（cron など）から poh-ttl scan を呼ぶだけ。
他クレートとの連携
poh_storage → TTL 機能をプラグイン的に拡張
将来的に poh_network などと組み合わせれば、期限切れトランザクションをネットワーク上でも再通知しないよう制御可能
これらにより、PoH システム全体のストレージ安全性とリソース効率を高められます。


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

#　wheel を dist\ に置きたいなら
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

pytest 用単体テスト。
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\pytest poh_ttl/tests

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_ttl>pytest poh_ttl/tests
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: D:\city_chain_project\DAGs\libs\algorithm\poh_ttl
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 2 items

poh_ttl\tests\test_cli.py .                                                                                      [ 50%]
poh_ttl\tests\test_manager.py .                                                                                  [100%]

================================================== 2 passed in 3.80s ==================================================
