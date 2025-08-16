rvh_filter (1) – ノード除外

以下は Python-only の軽量ユーティリティ rvh_filter (1) – ノード除外フィルター の「そのまま置けば動く」最小構成です。
（すべて UTF-8 / LF で保存してください）
rvh_filter/                     ← Git リポジトリ or サブツリー
├── README.md
├── LICENSE                     ← Apache-2.0 など
├── .gitignore                  ← __pycache__ / *.py[cod] / .venv など
├── pyproject.toml
└── rvh_filter/
    ├── __init__.py
    ├── _version.py
    ├── filter_core.py
    ├── cli.py
    └── tests/
        ├── __init__.py
        └── test_filter.py

📦 rvh_filter ― ノード除外ユーティリティ
rvh_filter は 「候補ノード集合」から動的に除外ルールを適用して
送信先・リーダー選定・シャード分散などの前段階で “使えるノード” だけをサッと抽出する
“軽量フィルター” ライブラリです。純-Python 実装なので追加ビルドは不要です ✅

1. 典型ユースケース
シーン	どんな除外を掛ける？	例
送信 DAG	一時的に落ちている / 過剰負荷ノードを外す	unhealthy={"n7","n9"}
VRF リーダー選	同一リージョンを重複させない	same_region={"us-east"}
Repair 要求	既にシャードを保持しているノードは除外	already_have={"n4"}

2. 関数シグネチャ
from rvh_filter import filter_nodes, FilterError

def filter_nodes(
    nodes: list[str],
    blacklist: set[str] | None = None,
    predicates: list[Callable[[str], bool]] | None = None,
) -> list[str]
引数	意味
nodes	フィルタ前の候補ノード
blacklist	ID ベースの静的除外
例: 落ちているノード集合
predicates	動的条件 (lambda / 関数) を並べたリスト
各 predicate が True を返したノードだけ残す

⚠️ すべて除外されると FilterError("no node left") を送出します。

3. クイックスタート
from rvh_filter import filter_nodes

nodes = ["n1","n2","n3","n4"]

# Blacklist と predicate を同時に掛ける例
active = filter_nodes(
    nodes,
    blacklist={"n3"},
    predicates=[
        lambda nid: not nid.startswith("n2"),   # n2 系は除外
    ]
)
print(active)  # → ['n1', 'n4']

4. 高速系コンポーネントとの組み合わせ
from rvh_filter import filter_nodes
from rvh_python import rendezvous_hash         # EC で既に作った高速ハッシュ

candidates = filter_nodes(all_nodes, blacklist=bad_nodes)
selected   = rendezvous_hash(candidates, tx_id, k=3)
rvh_filter で “使えるノード” を整え

rvh_python/rvh_rust で HRW スコア ⇒ 上位 k を決定

5. CLI ワンライナー
rvh_filter 単体には CLI を同梱していませんが、下記のように
ワンショットスクリプトを書けば簡易フィルタリングが行えます。
python - <<'PY'
from rvh_filter import filter_nodes
nodes      = "a,b,c,d".split(",")
blacklist  = {"b"}
result = filter_nodes(nodes, blacklist)
print("filtered =", result)
PY
# => filtered = ['a', 'c', 'd']

6. 失敗時のハンドリング
from rvh_filter import filter_nodes, FilterError

try:
    survivors = filter_nodes(["x"], blacklist={"x"})
except FilterError as e:
    # → "all nodes excluded"
    logger.warning("送信リトライをスキップ: %s", e)

7. テスト／CI の呼び出し
# pip install -e .

# python -m build --wheel --outdir dist

この後にテストする

# ルート or rvh_filter/ ディレクトリで
pytest -v rvh_filter/tests
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_filter>pytest -v rvh_filter/tests
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\DAGs\libs\algorithm\rvh_filter
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 7 items

rvh_filter/tests/test_filter.py::test_blacklist PASSED                                                           [ 14%]
rvh_filter/tests/test_filter.py::test_regex PASSED                                                               [ 28%]
rvh_filter/tests/test_filter.py::test_predicate PASSED                                                           [ 42%]
rvh_filter/tests/test_filter.py::test_error_regex PASSED                                                         [ 57%]
rvh_filter/tests/test_filter.py::test_async_blacklist PASSED                                                     [ 71%]
rvh_filter/tests/test_filter.py::test_async_regex_and_predicate PASSED                                           [ 85%]
rvh_filter/tests/test_filter.py::test_async_error_regex PASSED                                                   [100%]

================================================== 7 passed in 0.84s ==================================================


📝 まとめ
ブラックリスト と 動的 predicate を合成できる柔軟な API
依存ゼロの純-Python、サービス起動中でもホットリロードが容易
「フィルタ→HRW ハッシュ→EC 符号化」の前段としてシンプルに組み込み可能
これで 使えないノードを瞬時に排除 し、後続アルゴリズムをクリーンな入力で走らせられます！


(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_filter>pytest -v rvh_filter/tests/
============================================= test session starts ==============================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\DAGs\libs\algorithm\rvh_filter
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 4 items

rvh_filter/tests/test_filter.py::test_blacklist PASSED                                                    [ 25%]
rvh_filter/tests/test_filter.py::test_regex PASSED                                                        [ 50%]
rvh_filter/tests/test_filter.py::test_predicate PASSED                                                    [ 75%]
rvh_filter/tests/test_filter.py::test_error_regex PASSED                                                  [100%]

============================================== 4 passed in 0.54s ===============================================

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_filter>


✅ 補足：build について
このモジュールは Python のみなので、Rust のような cargo build は不要です。
ビルドしたい場合は wheel にパッケージングする意味になります：
pip install build
python -m build
これで dist/rvh_filter-0.1.0-py3-none-any.whl が生成されます。
