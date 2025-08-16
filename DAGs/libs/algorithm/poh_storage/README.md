poh_storage/                              ← リポジトリルート
├── LICENSE                              ← ライセンス (Apache-2.0 など)
├── README.md                            ← パッケージ概要・インストール手順・使い方
├── .gitignore                           ← __pycache__/、*.py[cod] など
├── pyproject.toml                       ← PEP 517/518 ビルド設定（依存関係、パッケージ名、バージョン等）
└── poh_storage/                         ← 実際の Python モジュール
    ├── __init__.py                      ← パッケージ定義（バージョン読み込みなど）
    ├── app_storage.py                   ← エンドポイント    
    ├── storage.py                       ← `StorageManager` クラス（Tx の登録／取得／削除の高レベル API）
    ├── hash_utils.py                    ← SHA-256 ハッシュ計算ユーティリティ
    ├── file_store.py                    ← ファイルベースの永続化 (ディレクトリ構造管理、ファイル I/O)
    ├── sqlite_store.py                  ← SQLite ベースの永続化 (テーブル定義、CRUD)
    ├── recovery.py                      ← 起動時リカバリ／不整合検出＆修復ロジック
    └── tests/                           ← 単体テスト
        ├── __init__.py
        ├── test_storage.py              ← `StorageManager` の振る舞いテスト
        ├── test_hash_utils.py           ← SHA-256 計算のテスト
        ├── test_file_store.py           ← ファイル I/O のテスト
        ├── test_sqlite_store.py         ← SQLite CRUD のテスト
        └── test_recovery.py             ← リカバリ処理のテスト

以下は poh_storage パッケージが提供する主な機能と、その内部構成の詳細な解説です。

1. データモデル（types.py / tx.py）
Tx
@dataclass
class Tx:
    tx_id:     str
    holder_id: str
    timestamp: float
    payload:   bytes

tx_id：一意なトランザクション識別子
holder_id：オリジナルデータの保持者 ID
timestamp：発行時刻（UNIX エポック秒）
payload：バイナリペイロード（実際の取引データ等）
types.py フェイサー
将来外部の poh_types パッケージを導入したときに、自動的にそちらの Tx を使えるようにする小さなラッパーです。

2. ハッシュユーティリティ（hash_utils.py）
sha256_hex(data: bytes) -> str
入力バイト列の SHA-256 ダイジェストを 16 進文字列で返す
メタデータ（ファイル保存後の整合性検証）に使用

3. ファイルベース永続化（file_store.py）
FileStore（完全非同期）
save(key, data)：<base_path>/<key>.bin にバイト列を書き込む
load(key) -> bytes：同ファイルを読み出す
exists(key) -> bool：ファイルの有無をチェック
remove(key)：該当ファイルを削除
list_keys() -> list[str]：*.bin のキー一覧を返す
内部で aiofiles を使い、I/O 待ち中も他タスクを実行可能

4. SQLite ベース永続化（sqlite_store.py）
SQLiteStore（完全非同期）
init()：テーブル txs(tx_id TEXT PRIMARY KEY, storage_hash TEXT, timestamp REAL) を作成
save(tx_id, storage_hash, timestamp)：メタデータを INSERT/REPLACE
load(tx_id) -> Optional[(storage_hash, timestamp)]：単一行取得
remove(tx_id)：DELETE
list_ids() -> list[str]：登録済み tx_id の一覧を返す
内部で aiosqlite を利用

5. 高レベル API（storage.py）
StorageManager
create(base_path, sqlite_path)：FileStore＋SQLiteStore を初期化して返す
save_tx(tx: Tx)
payload の SHA-256 を計算
FileStore.save(tx_id, payload)
SQLiteStore.save(tx_id, hash, timestamp)
load_tx(tx_id) -> Tx \| None
メタ取得 (load)、ファイル読み出し (load)
ハッシュ検証（不一致なら例外）
正常なら Tx(...) を復元して返す
list_txs() -> list[str]：登録済み ID 一覧
delete_tx(tx_id)：ファイル & SQLite 行を両方削除
recover() -> list[str]
list_txs() で得たすべての ID について load_tx() を試み
整合性エラーが起きたものは delete_tx() してスキップ
成功した ID のみリストで返す

close()
aiosqlite コネクションをクローズ
asyncio の ThreadPoolExecutor をシャットダウン
テスト＆CLI 終了時に必ず呼び出し、リーク防止

6. 起動時リカバリユーティリティ（recovery.py）
perform_recovery(base_path, sqlite_path)
StorageManager.create()
await manager.recover() を実行し、ログ出力
最後に await manager.close()
アプリ起動時に自動実行して、古い／破損データを掃除

7. コマンドラインインターフェイス（app_storage.py）
サブコマンド：init, save, load, delete, list, recover
argparse でパーサ定義
非同期エントリポイント async def main() を用意し、最後に asyncio.run(main())
Windows 対策：必要なら asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

実行例：
poh-storage init   --base ./data --db ./data/poh.db
poh-storage save   --base ./data --db ./data/poh.db --tx '{"tx_id":"1","holder_id":"h","timestamp":0.0,"payload":"..."}'
poh-storage list   --base ./data --db ./data/poh.db
poh-storage load   --base ./data --db ./data/poh.db --tx-id 1
poh-storage recover--base ./data --db ./data/poh.db
終了時に必ず manager.close() を呼び、バックグラウンドの I/O リソースを解放

8. テスト設計
ユニットテスト
test_hash_utils.py, test_file_store.py, test_sqlite_store.py, test_storage.py, test_recovery.py
いずれも非同期リソースを最後にクローズする finally: await close() を実装

CLI 結合テスト
test_cli.py では Python subprocess を利用だが、フリーズするので凍結した！
Windows 環境でのハング対策としてバッファの扱いやタイムアウトを調整

まとめ
poh_storage は 非同期で
バイナリファイル保存
SQLite メタデータ管理
整合性チェック＆リカバリ
CLI およびプログラム的 API
を一貫して提供するクレートです。

将来、poh_types を切り出す場合も フェイサーモジュール でサクッとスワップ可能な設計になっています。
運用・拡張性・テストカバレッジすべてを考慮した、堅牢なストレージレイヤーです。



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
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_storage\pytest poh_storage/tests

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_storage>pytest poh_storage/tests
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: D:\city_chain_project\DAGs\libs\algorithm\poh_storage
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 5 items

poh_storage\tests\test_file_store.py .                                                                           [ 20%]
poh_storage\tests\test_hash_utils.py .                                                                           [ 40%]
poh_storage\tests\test_recovery.py .                                                                             [ 60%]
poh_storage\tests\test_sqlite_store.py .                                                                         [ 80%]
poh_storage\tests\test_storage.py .                                                                              [100%]

================================================== 5 passed in 0.39s ==================================================


#　poh_types\への依存がここで発覚！どう解消する？
以下のように進めると、今は poh_storage/tx.py に定義したまま、あとで外部の poh_types パッケージを導入したときに最小限の変更で置き換えられるようになります。

1. 今のうちに poh_storage/tx.py を作る
# poh_storage/tx.py

from dataclasses import dataclass

@dataclass
class Tx:
    tx_id:     str
    holder_id: str
    timestamp: float
    payload:   bytes
全コード／テストでこの Tx を使っておきます。

2. フェイサーモジュール poh_storage/types.py を作る
# poh_storage/types.py

try:
    # 後で poh_types が pip install されていればこちらを優先
    from poh_types.tx import Tx
except ImportError:
    # なければローカルの tx.py を使う
    from .tx import Tx

__all__ = ("Tx",)

これで、アプリ＆テストはすべて
from poh_storage.types import Tx
と書くだけで OK になります。

3. コード／テストの修正例
storage.py
-from poh_storage.tx import Tx
+from poh_storage.types import Tx

test_storage.py
-from poh_storage.tx import Tx
+from poh_storage.types import Tx

他のファイルも同様に from poh_storage.types import Tx に統一してください。

4. 後で別パッケージ poh_types を出すとき
poh_types/tx.py に同じ Tx 定義を置いて PyPI などに公開
プロジェクトの依存に poh_types>=0.1.0 を追加
開発環境で pip install poh_types すると、フェイサーの import poh_types.tx が成功して
→ poh_storage/tx.py のスタブは自動的に無視されます
必要であればスタブを消すだけ
―――

この方法のメリット
あとから一切の find/replace 不要
フェイサー (types.py) １ファイルだけで「どちらの Tx 定義を使うか」を切り替え
開発中は外部依存なし、本番だけ poh_types を入れる、が自然にできる
こうしておけば、将来 poh_types を独立パッケージ化してもコードの変更はほぼゼロ、運用もスムーズです。
すばらしい！