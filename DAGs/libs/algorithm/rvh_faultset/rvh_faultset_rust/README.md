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
│   │       ├── test_faultset.rs                  ← Rust 単体テスト
│   │ 　    └── test_cli.rs    　　　　　　　　　　 ← CLIテスト
│   │ 　    └── test_py_bindings.rs    　　　　　　← pyo3 経由で呼び出し
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

以下、rvh_faultset の機能概要と使い方をまとめました。

機能概要
Latency‐based Failover (Rust core)

failover(nodes: &[String], latencies: &[f64], threshold: f64) -> Result<Vec<String>, FaultsetError>
与えられたノード ID リストとそれぞれのレイテンシ（ms）をしきい値でフィルタし、許容内のノードをレイテンシ昇順で返します。

エラー条件：
ノードリストが空 → FaultsetError::EmptyNodes
ノード数とレイテンシ数の不一致 → FaultsetError::LengthMismatch
閾値が負 → FaultsetError::NegativeThreshold
Python バインディング (PyO3)
Rust 実装をそのまま rvh_faultset.failover(nodes, latencies, threshold) で呼び出せます。
失敗時は ValueError で例外が上がります。

CLI ツール
Rust 側バイナリ main_faultset と、Python 側 python -m rvh_faultset.app_faultset の両方を用意。
たとえば：
# Rust CLI
main_faultset \
  --nodes "nodeA,nodeB,nodeC" \
  --latencies "50,200,75" \
  --threshold 100.0
# 出力: nodeA,nodeC

# Python CLI
python -m rvh_faultset.app_faultset \
  --nodes nodeA,nodeB,nodeC \
  --lats 50,200,75 \
  --th 100
使い慣れた言語／環境で選べます。

ベンチマーク
1,000 ノード規模でのシングルスレッド/マルチスレッド性能を Criterion で測定。
並列版では Rayon を使い、par_iter() で高速集計。

Rust での使い方
use rvh_faultset_rust::faultset::failover;
use rvh_faultset_rust::error::FaultsetError;

fn main() -> Result<(), FaultsetError> {
    let nodes = vec![
        "a".to_string(),
        "b".to_string(),
        "c".to_string(),
    ];
    let lats = vec![50.0, 150.0, 75.0];
    let threshold = 100.0;

    let healthy = failover(&nodes, &lats, threshold)?;
    println!("Healthy nodes: {:?}", healthy);
    // → ["a", "c"]
    Ok(())
}

エラー例
match failover(&[], &[], 100.0) {
    Err(FaultsetError::EmptyNodes) => eprintln!("ノードが指定されていません"),
    _                             => unreachable!(),
}

Python での使い方
インストール
# PyPI から
pip install rvh_faultset_rust

・API
from rvh_faultset import failover

nodes    = ["a", "b", "c"]
latencies= [50.0, 150.0, 75.0]
threshold= 100.0

try:
    healthy = failover(nodes, latencies, threshold)
    print("Healthy:", healthy)  # → ['a', 'c']
except ValueError as e:
    print("Error:", e)

・Python CLI
python -m rvh_faultset.app_faultset \
    --nodes a,b,c \
    --lats 50,150,75 \
    --th 100
# Healthy nodes: ['a', 'c']

・統合テスト例
# rvh_faultset_integration.py
import pytest
from rvh_faultset import failover

def test_failover_basic():
    nodes = ["n1","n2","n3"]
    lats  = [10.0, 200.0, 50.0]
    assert failover(nodes, lats, 100.0) == ["n1","n3"]

def test_error_negative():
    with pytest.raises(ValueError):
        failover(["n1"], [10.0], -5.0)

・CI/CD
GitHub Actions (.github/workflows/ci.yml) で以下を自動実行：
cargo test
maturin build && maturin test
pytest
cargo bench

これでレイテンシしきい値によるフォールバック選定機能を、Rust／Python 双方からシームレスに利用できます。


#　テスト準備
なぜ必要なのか
pyo3-build-config::add_extension_module_to_path! マクロは 0.21 系に移動した、または非推奨になっており、0.18 系には存在しません。

そこで手動でビルド済みの .so/.dylib/.dll を探し
Windows なら .dll→.pyd にコピー
そのディレクトリを PYTHONPATH に追加
といった処理を行うことで、テスト実行時に Python が拡張モジュールを正しく読み込めるようにします。
これで cargo test → Rust 側全テスト、さらに Python バインディングのテストまで一気通貫でパスするはずです。

・まずは.dll は下記にある
D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\target\debug\deps\rvh_faultset_rust.dll

・つぎに、.pyd をコピーする
D:\city_chain_project\.venv312\Lib\site-packages\rvh_rust\rvh_rust.cp312-win_amd64.pyd
ここにあるわ。

・テストコードを修正するポイントまとめ
find_cdylib() …target/{debug,release}/deps/ 以下を再帰検索して拡張モジュールファイル（.dll / .so / .dylib）を見つけます。
ensure_pyd() …Windows では .dll を .pyd にコピー。Linux/macOS はそのまま使います。
add_pythonpath() …拡張モジュールのあるディレクトリを PYTHONPATH に追加し、テスト中の Python インタープリタがモジュールを見つけられるようにします。
以降は py.import("rvh_faultset_rust") で正常にロードできるはずです。

・ Maturin で先にインストールしてしまう
開発マシン・CI 共に少し手順を増やしてよいなら、テストの前に maturin develop --release（または pip install .）で拡張モジュールを仮想環境にインストールしてしまうのが簡単です。
そうすれば、cargo build → cargo test ではなく、次のように流せば OK:
cd rvh_faultset_rust
maturin develop --release
cd ../rvh_faultset_python
pip install .   # or pip install -e .
cd ../
cargo test      # Python の mv はもう不要
CI の .github/workflows/ci.yml にも、この手順を足してください。

# lib.rsへの追加
pub mod rendezvous;
pub mod utils;  // ← これが必要！
mod bindings;          // ← #[pymodule] を含む

pub use rendezvous::{rendezvous_hash, RendezvousError};
pub use bindings::*;   // Python ラッパーを re-export

これを入れておけば、cargo test（あるいは CI 上での cargo test）だけで、Rust のユニットテスト・CLI テスト・Python バインディングテストまで一貫して動作確認できるようになります。

src/lib.rs に mod bindings; pub use bindings::*; を必ず追加
cargo build または maturin develop --release → 上記のテストを再実行

これで .pyd／.so に正しい PyInit_rvh_faultset_rust シンボルが含まれ、Python 側からも問題なく import rvh_faultset_rust に成功するはずです。

✅ まとめ
問題点	解決策
target/debug に .pyd がない	正常です、.pyd は仮想環境の site-packages に入ります
Rustのテストで .pyd を探している	find_shared_lib() は不要、Pythonから直接 import を試すコードに変える
.whl ができてるけど .pyd が見えない	pip install すれば .pyd が見えるようになります
ポイントまとめ
必ず「動いている」ループの中で Rust の async binding を await する必要があります。

Python のトップレベルで直接呼び出してしまうと、asyncio.get_running_loop() が失敗してしまいます。

そのため、上記のように Python 側で async def _main(...) を定義し、その中で await rvh_faultset_rust.failover_async(...) するスタイルに合わせてください。

running 4 tests
test empty_nodes ... ok
test length_mismatch ... ok
test negative_threshold ... ok
test selection ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_import.rs (target\debug\deps\test_import-d35b36a64ce7bd08.exe)

running 1 test
test python_import_only ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.09s

     Running tests\test_py_bindings.rs (target\debug\deps\test_py_bindings-ac229e101d1f9eb4.exe)

running 1 test
Executing <Task pending name='Task-1' coro=<_main() running at <string>:4> wait_for=<Future pending cb=[<builtins.PyDoneCallback object at 0x000001C03F076230>(), Task.task_wakeup()] created at D:\Python\Python312\Lib\asyncio\base_events.py:448> cb=[_run_until_complete_cb() at D:\Python\Python312\Lib\asyncio\base_events.py:181] created at D:\Python\Python312\Lib\asyncio\tasks.py:695> took 0.172 seconds
test python_module_roundtrip ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.65s

   Doc-tests rvh_faultset_rust

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


# ベンチ (結果は target/criterion/)
cargo bench --bench bench_faultset

    Finished `bench` profile [optimized] target(s) in 51.22s
     Running benches\bench_faultset.rs (target\release\deps\bench_faultset-af4d1293156a63ec.exe)
failover_all/serial/1000
                        time:   [56.918 µs 58.226 µs 59.957 µs]
                        thrpt:  [16.679 Melem/s 17.174 Melem/s 17.569 Melem/s]
Found 5 outliers among 50 measurements (10.00%)
  4 (8.00%) high mild
  1 (2.00%) high severe
failover_all/parallel/1000
                        time:   [223.20 µs 228.02 µs 233.61 µs]
                        thrpt:  [4.2807 Melem/s 4.3856 Melem/s 4.4802 Melem/s]
Found 2 outliers among 50 measurements (4.00%)
  2 (4.00%) high mild
failover_all/async/1000 time:   [188.52 µs 197.66 µs 208.38 µs]
                        thrpt:  [4.7990 Melem/s 5.0592 Melem/s 5.3044 Melem/s]
Found 9 outliers among 50 measurements (18.00%)
  3 (6.00%) high mild
  6 (12.00%) high severe
failover_all/serial/10000
                        time:   [578.62 µs 594.61 µs 614.97 µs]
                        thrpt:  [16.261 Melem/s 16.818 Melem/s 17.282 Melem/s]
Found 3 outliers among 50 measurements (6.00%)
  3 (6.00%) high severe
failover_all/parallel/10000
                        time:   [794.61 µs 804.91 µs 815.07 µs]
                        thrpt:  [12.269 Melem/s 12.424 Melem/s 12.585 Melem/s]
Found 2 outliers among 50 measurements (4.00%)
  2 (4.00%) high mild
failover_all/async/10000
                        time:   [1.5038 ms 1.5387 ms 1.5812 ms]
                        thrpt:  [6.3244 Melem/s 6.4988 Melem/s 6.6500 Melem/s]
Found 9 outliers among 50 measurements (18.00%)
  4 (8.00%) high mild
  5 (10.00%) high severe
Benchmarking failover_all/serial/100000: Warming up for 2.0000 s
Warning: Unable to complete 50 samples in 5.0s. You may wish to increase target time to 9.5s, enable flat sampling, or reduce sample count to 20.
failover_all/serial/100000
                        time:   [7.1837 ms 7.4734 ms 7.7809 ms]
                        thrpt:  [12.852 Melem/s 13.381 Melem/s 13.920 Melem/s]
Found 6 outliers among 50 measurements (12.00%)
  4 (8.00%) high mild
  2 (4.00%) high severe
Benchmarking failover_all/parallel/100000: Warming up for 2.0000 s
Warning: Unable to complete 50 samples in 5.0s. You may wish to increase target time to 5.7s, enable flat sampling, or reduce sample count to 30.
failover_all/parallel/100000
                        time:   [4.2815 ms 4.4111 ms 4.5400 ms]
                        thrpt:  [22.026 Melem/s 22.670 Melem/s 23.357 Melem/s]
failover_all/async/100000
                        time:   [17.276 ms 17.672 ms 18.158 ms]
                        thrpt:  [5.5072 Melem/s 5.6586 Melem/s 5.7884 Melem/s]
Found 3 outliers among 50 measurements (6.00%)
  1 (2.00%) high mild
  2 (4.00%) high severe
