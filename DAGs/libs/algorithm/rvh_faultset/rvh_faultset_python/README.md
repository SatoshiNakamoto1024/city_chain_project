rvh_faultset/                                     ← リポジトリルート
├── README.md                                     ← プロジェクト概要・ビルド & テスト手順
├── LICENSE                                       ← Apache-2.0 など
├── rvh_faultset_integration.py                   ← rust・pythonの統合テスト
├── .gitignore                                    ← target/, __pycache__/ など
├── .github/
│   └── workflows/
│       └── ci.yml                                ← cargo test → maturin build → pytest → cargo bench
│
├── rvh_faultset_rust/                            ← Rust コア & Pythonバインディング
│   ├── Cargo.toml
│   ├── pyproject.toml　　　　　　　　　　　　　　  ← Rust側のbist\吐き出し用
│   ├── src/
│   │   ├── lib.rs                                ← `pub mod faultset; pub mod error; pub use faultset::*;`
│   │   ├── faultset.rs                           ← 障害時フォールバックアルゴリズム本体
│   │   ├── error.rs                              ← `#[derive(Error)]` 共通エラー型
│   │   ├── bindings.rs                           ← PyO3 での `#[pymodule]` ラッパー
│   │   ├── main_faultset.rs                      ← CLI サンプル (`--bin main_faultset`)
│   │   └── tests/
│   │       └── test_faultset.rs                  ← Rust 単体テスト
│   └── benches/
│       ├── bench_faultset_failover.rs            ← failover ベンチマーク
│       └── bench_faultset_parallel.rs            ← 並列ベンチマーク
│
└── rvh_faultset_python/                          ← Pythonサイドラッパー & pure-Python geohash
    ├── __init__.py
    ├── pyproject.toml                            ← Python側のbist\吐き出し用
    ├── README.md                                 ← Python向け使用例・インストール手順
    ├── rvh_faultset/                             ← Pythonパッケージ本体
        ├── __init__.py
        ├── _version.py
        ├── geohash.py                            ← レイテンシ最適化用 geohash 実装（Python-only）
        ├── faultset_builder.py                   ← geohash→faultset 統合パイプライン
        ├── app_faultset.py                       ← CLIサンプル (`python -m rvh_faultset.app_faultset`)
        └── tests/
            └── test_faultset.py         　　　　　　　← pytest テスト

#　以下、rvh_faultset_python の機能概要と使い方をまとめました。
rvh_faultset_python パッケージは、地理的に近いノード同士をクラスタ化（Geohash）→**各クラスタごとに閾値以下のノードを選出（フェイルオーバー）**という２段階パイプラインを提供します。Rust 実装の failover を呼び出す橋渡しも行うので、パフォーマンスと可搬性を両立できます。

主な機能
Geohash クラスタリング（geohash.py）
緯度・経度→ビット操作で Base32 字符列に変換し、同じプレフィックスを持つノード群を同一クラスタとみなします。
from rvh_faultset.geohash import encode
gh1 = encode(35.6895, 139.6917, precision=5)  # e.g. 'xn774'
gh2 = encode(35.6890, 139.6920, precision=5)  # gh1 と同じクラスタになる

フェイルオーバー選出（faultset_builder.py）
faultset(nodes, threshold, precision)
from rvh_faultset import faultset, FaultsetError

# ノード情報の例（id, lat, lon, latency）
NODES = [
    {"id": "a", "lat": 35.0, "lon": 139.0, "latency":  50.0},
    {"id": "b", "lat": 51.5, "lon":  -0.1, "latency": 200.0},
    {"id": "c", "lat": 40.7, "lon":  -74.0, "latency":  75.0},
]

try:
    survivors = faultset(NODES, threshold=100.0, precision=5)
    # → ['a','c']
except FaultsetError as e:
    # ノードリスト空、またはすべてフィルタ後に残らない場合に発生
    print("エラー:", e)
FaultsetError

ノードリスト空：FaultsetError("nodes is empty")
全クラスタで残存ノードなし：FaultsetError("all clusters yielded no survivors")

CLI（app_faultset.py）
python -m rvh_faultset.app_faultset \
  --nodes a:35.0:139.0:50.0,b:51.5:-0.1:200.0,c:40.7:-74.0:75.0 \
  --threshold 100.0 --precision 5
とすると、標準出力にサバイバーの ID リストが表示されます。

#　インストールとテスト
Rust バックエンドをビルド＆インストール
cd rvh_faultset_rust
maturin develop --release

Python パッケージをインストール
cd ../rvh_faultset_python
pip install -e .

#　wheel を dist\ に置きたいなら
python -m build --wheel --outdir dist（Python ラッパも含め全部）


#　テスト方法
# CLI 動作確認
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python>python -m rvh_faultset.app_faultset -n "n1:35.0:139.0:50,n2:51.5:-0.1:200,n3:40.7:-74.0:75" -t 100.0 -p 5 --async --level debug
Executing <Task pending name='Task-1' coro=<faultset_async() running at D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\rvh_faultset\faultset_builder.py:93> wait_for=<Future pending cb=[<builtins.PyDoneCallback object at 0x0000024B77429050>(), Task.task_wakeup()] created at D:\Python\Python312\Lib\asyncio\base_events.py:448> cb=[_run_until_complete_cb() at D:\Python\Python312\Lib\asyncio\base_events.py:181] created at D:\Python\Python312\Lib\asyncio\runners.py:100> took 0.109 seconds
Survivors: ['n1', 'n3']

# 単体テスト
$ pytest rvh_faultset/tests -q
......
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python>pytest rvh_faultset/tests -q
.....                                                                                                            [100%]
5 passed in 1.33s

統合テスト（rvh_faultset_integration.py）
Pure-Python→Rustフェイルオーバー→最終結果まで正しく動作するかを確認するスクリプトを用意しています。

内部処理フロー
入力検証
空リストなら即座に例外。
Geohash でクラスタ化
緯度経度から同一プリフィックスの文字列を得て、同じクラスタにノードを集約。
クラスタごとにフェイルオーバー呼び出し
Rust 実装（高速） or Python 実装（フォールバック）で failover(nodes, latencies, threshold) を呼び出し。
しきい値以下のノードだけを残し、一切残らないクラスタはスキップ。

最終結果
全クラスタをマージし、サバイバーが空なら例外、そうでなければ ID リストを返す。

まとめ
GeoHash で地理的に近いノードをまとめ、
フェイルオーバー で閾値以下のノードだけ選出、
Rust バックエンドと Python フォールバックのハイブリッド実装。

この組み合わせにより、レイテンシ最適化＋障害時フォールバックを簡単に導入できます。何かご不明点があれば、またお気軽にどうぞ！


#　ビルドが先
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python>pip install -e .
Obtaining file:///D:/city_chain_project/DAGs/libs/algorithm/rvh_faultset/rvh_faultset_python
  Installing build dependencies ... done
  Checking if build backend supports build_editable ... done
  Getting requirements to build editable ... done
  Preparing editable metadata (pyproject.toml) ... done
Requirement already satisfied: rvh_faultset_rust>=0.1.0 in d:\city_chain_project\.venv312\lib\site-packages (from rvh_faultset==0.1.0) (0.1.0)
Building wheels for collected packages: rvh_faultset
  Building editable for rvh_faultset (pyproject.toml) ... done
  Created wheel for rvh_faultset: filename=rvh_faultset-0.1.0-0.editable-py3-none-any.whl size=3964 sha256=70af0ca4fd59a81815e7c9571cd4ed761db9424db3166ac2f09fcf7beb6a0abd
  Stored in directory: C:\Users\kibiy\AppData\Local\Temp\pip-ephem-wheel-cache-_aon4mw8\wheels\d4\2f\39\71f2cf3eec837cc9ab80e9c4b27989166480c5574aa35418ea
Successfully built rvh_faultset
Installing collected packages: rvh_faultset
Successfully installed rvh_faultset-0.1.0

#　テスト方法
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python>pytest -v rvh_faultset/tests/
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 3 items

rvh_faultset\tests\test_faultset.py::test_basic_faultset PASSED                                                  [ 33%]
rvh_faultset\tests\test_faultset.py::test_empty_nodes PASSED                                                     [ 66%]
rvh_faultset\tests\test_faultset.py::test_cluster_empty PASSED                                                   [100%]

================================================== 3 passed in 0.16s ==================================================
