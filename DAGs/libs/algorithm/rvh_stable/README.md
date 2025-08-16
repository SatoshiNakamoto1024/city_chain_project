以下のように、Python-only のパッケージとして rvh_stable を構成します。Rust は不要です。Jump Consistent Hash を純粋 Python で実装し、同期／非同期両方の API、CLI、テスト、パッケージ設定を含んだ「本番想定」構成です。

rvh_stable/                           ← リポジトリルート
├── LICENSE
├── README.md
├── .gitignore
├── pyproject.toml                    ← Maturin ではなく setuptools／PEP 517 用
│
├── rvh_stable/                       ← Python パッケージ本体
│   ├── __init__.py
│   ├── stable.py                     ← Jump Hash 実装(sync + async)
│   ├── cli.py                        ← CLI (--async オプション対応)
│   └── tests/
│       ├── __init__.py
│       └── test_stable.py            ← pytest テスト
└── .github/
    └── workflows/
        └── ci.yml                   ← GitHub Actions CI 設定

各ファイルの役割
pyproject.toml
setuptools を使ったビルド／インストール設定。依存は標準ライブラリのみ。

rvh_stable/__init__.py
パッケージのバージョン取得と公開 API (jump_hash, jump_hash_async, main など) のエクスポート。

rvh_stable/stable.py
Jump Consistent Hash の純 Python 実装（Google 版）。

def jump_hash(key: int, num_buckets: int) -> int

async def jump_hash_async(key: int, num_buckets: int) -> int
└ asyncio.get_running_loop().run_in_executor(...) で非同期実行。

rvh_stable/cli.py
python -m rvh_stable.cli または rvh-stable スクリプトで呼び出す CLI。
--key、--buckets、--async フラグをサポート。


#　wheel を dist\ に置きたいなら
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

pytest 用単体テスト。
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_stable\pytest rvh_stable/tests
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_stable>pytest rvh_stable/tests
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: D:\city_chain_project\DAGs\libs\algorithm\rvh_stable
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 9 items

rvh_stable\tests\test_cli.py ...                                                                                 [ 33%]
rvh_stable\tests\test_stable.py ......                                                                           [100%]

================================================== 9 passed in 0.62s ==================================================


# 概要
rvh_stable は、Google の Jump Consistent Hash（通称 Jump Hash）アルゴリズムを純粋 Python で実装し、同期・非同期（asyncio）呼び出しと CLI を提供する軽量モジュールです。以下、機能と内部動作を詳しく見ていきます。

1. Jump Consistent Hash とは？
目的：与えられたキー（例：トランザクション ID）を固定数のバケット（例：シャード ID）に一貫してマッピングする。

特長：
O(1) 時間で計算できる
各キーは常に同じバケットに割り当てられ、バケット数が変化しても再配置されるキーの数が最小になる
メモリ不要、ハッシュ関数に基づくだけ

2. API 構成
2.1 同期版：jump_hash(key: str, buckets: int) -> int
from rvh_stable import jump_hash

shard = jump_hash("tx42", 10)

# => 0 から 9 の整数を返す
引数
key：任意の文字列。内部で 64-bit 整数に変換し、Jump Hash の乱数シーケンスを生成。
buckets：総バケット数。返り値は 0 <= shard < buckets。

返り値：選ばれたバケット番号（整数）。

2.2 非同期版：async_jump_hash(key: str, buckets: int) -> Awaitable[int]
import asyncio
from rvh_stable import async_jump_hash

async def main():
    shard = await async_jump_hash("tx42", 10)
    print(shard)

asyncio.run(main())
同期版を内部で asyncio.get_running_loop().run_in_executor(...) に投げているだけなので、計算自体はブロックせず、他のコルーチンと並行実行可能です。

3. CLI サポート
app_stable.py で提供するコマンドラインインターフェイスは次のとおり：
$ python -m rvh_stable.app_stable \
    --key TX12345 \
    --buckets 7 \
    [--async] \
    [--level {debug,info,warn}]
--key, -k：ハッシュ対象の文字列

--buckets, -b：バケット数

--async, -a：付けると非同期版を動かす

--level, -l：ログレベル（デバッグ出力を制御。現在は起動ログのみ）

動作例：
$ python -m rvh_stable.app_stable -k foo -b 5
2
$ python -m rvh_stable.app_stable -k foo -b 5 --async
# 同じく 0–4 の整数を返す
起動時には stderr に "Executing <Task ...> took X.XXX seconds" といった実行ログを出力し（--level debug 時のみ）、stdout には最終的なバケット番号だけが出力されます。

4. 内部実装のポイント
64-bit 整数化
hashlib.blake3 等ではなく、Python 標準の hash() から 64 ビットを取り出して使用。

Jump Hash コアループ
def jump_hash(key, buckets):
    key64 = _to_u64(key)
    b = -1
    j = 0
    while j < buckets:
        b = j
        key64 = key64 * 2862933555777941757 + 1
        j = int((b + 1) * (1 << 31) / ((key64 >> 33) + 1))
    return b

asyncio 対応
async def async_jump_hash(key, buckets):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, jump_hash, key, buckets)
エラーハンドリング

buckets < 1 や key が空文字列のときは即時 ValueError を投げる。
CLI ではキャッチして exit code 1。

5. テストカバレッジ
ユニットテスト（tests/test_stable.py）
複数キー・バケット数での分布検証
境界値（buckets=1、大きなキー）
CLI テスト（tests/test_cli.py）
同期・非同期モード双方を subprocess で起動し、
exit code が 0、stdout が数字のみ、stderr が空、を確認

6. 主なユースケース
分散キャッシュ：リクエストキーを常に同じキャッシュサーバにルーティング
シャーディング：データベース／キューのバケット割当
負荷分散：ランダム性を含みつつもキーごとに固定先を維持
システム統合：純 Python なので、サーバレスや軽量マイクロサービスで依存ゼロに近く使える

7. 他モジュールとの連携
rvh_simd を使う必要がないため依存はありませんが、
将来的に同様の async/CLI パターンで Rust バックエンドを呼び出す拡張も可能です。

まとめ
rvh_stable は、Jump Hash を純 Python で手軽に使えるライブラリです。
すぐに導入できるシンプル API
asyncio／CLI 両対応
O(1)・メモリフリー・再配置最小という Jump Hash の利点をそのまま享受できます。
キャッシュレイヤーやシャード管理、分散システムのルーティングにぜひご活用ください！
