poh_holdmetrics/                                 ← リポジトリルート
├── README.md                                    ← プロジェクト概要・使い方
├── LICENSE                                      ← Apache-2.0 など
├── poh_holdmetrics_integration.py               ← Rust↔Python 結合シナリオ（pytest で実行）
├── .gitignore                                   ← /target, __pycache__, *.so, dist/
├── .github/
│   └── workflows/
│       └── ci.yml                               ← cargo test → maturin build → pytest → cargo bench
│
├── poh_holdmetrics_rust/                        ← Rust コア & PyO3 バインディング
│   ├── Cargo.toml                               ← crate 名: poh_holdmetrics_rust
│   ├── pyproject.toml                           ← maturin-build設定（abi3-py312）
│   ├── build.rs
│   ├── benches/
│   │   ├── bench_holdmetrics_calc.rs            ← スコア計算性能測定
│   │   └── bench_holdmetrics_parallel.rs        ← 並列集計ベンチ
│   ├── src/
│   │   ├── lib.rs                               ← `pub mod holdset; pub mod error; pub use holdset::*;`
│   │   ├── holdset.rs                           ← 保有時間→ポイント算出アルゴリズム（高速化部分）
│   │   ├── grpc.rs                              ← grpc exporting
│   │   ├── model.rs                             ← Shared data structures
│   │   ├── metrics.rs                           ← Prometheus gauge ・ counter initialisation
│   │   ├── error.rs                             ← `thiserror::Error` 共通エラー
│   │   ├── bindings.rs                          ← `#[pymodule]`・`#[pyfunction]` PyO3 ラッパ
│   │   └── main_holdmetrics.rs                  ← `--bin main_holdmetrics` CLI デモ
│   └── tests/
│       ├── test_cli.rs
│       ├── test_import.rs
│       ├── test_metrics.rs                      ← Prometheus メトリクス テスト
│       ├── test_grpc.rs                         ← gRPC I/O テスト
│       ├── test_py_bindings.rs
│       └── test_holdmetrics.rs                  ← Rust 単体テスト
│
└── poh_holdmetrics_python/
    ├── pyproject.toml                           ← Poetry/ Hatch 等 (poh-holdmetrics 名)
    ├── README.md                                ← pip インストール例・API 使用例
    └── poh_holdmetrics/                         ← Python パッケージ & 周辺ユーティリティ
        ├── __init__.py                              ← Rust 拡張のリロード & 公開 API
        ├── _version.py                              ← 自動生成版 + `importlib.metadata`
        ├── config.py                                ← TOML/YAML + env 取り込み
        ├── data_models.py                           ← Pydantic: HoldEvent / HoldStat …
        ├── tracker.py                               ← 非同期保持トラッカー (`record_start/stop`)
        ├── calculator.py                            ← Rust FFI 経由スコア計算 + fallback Pure-Py
        ├── scheduler.py                             ← `asyncio.TaskGroup` 周期集計・GC
        ├── app_holdmetrics.py                       ← `python -m poh_holdmetrics.app_holdmetrics` CLI
        │
        ├── exporter/                                ← 可観測性レイヤ
        │   ├── __init__.py
        │   ├── prometheus.py                        ← /metrics エンドポイント
        │   └── otlp.py                              ← OTEL Push / Pull
        │
        ├── storage/                                 ← プラガブル永続化
        │   ├── __init__.py
        │   ├── mongo.py                             ← motor 非同期ドライバ
        │   └── immudb.py                            ← aiogrpc → immuDB
        │
        ├── api/                                     ← ネットワーク I/F
        │   ├── __init__.py
        │   ├── grpc_server.py                       ← AIO gRPC: HoldEvent ストリーム
        │   └── http_server.py                       ← FastAPI: /hold, /stats, /healthz
        │
        ├── protocols/                               ← Protobuf 生成物（自動生成ディレクトリごと commit）
        │   ├── hold.proto
        │   └── hold_pb2_grpc.py
        │
        └── tests/                                   ← pytest & pytest-asyncio
            ├── __init__.py
            ├── test_tracker.py
            ├── test_calculator.py
            ├── test_scheduler.py
            ├── test_storage.py
            └── test_api.py

poh_holdmetrics_rust クレート ─ 機能一覧と内部構造
目的
Solana の “Proof-of-Hold (PoH)” 風 アルゴリズムを Rust で実装し、
スコア計算ロジック（ライブラリ）
インメモリ集計器（マルチスレッド安全）
gRPC サービス ＆ Prometheus Exporter（バイナリ）
PyO3 バインディング（Python から直接利用）
をワンストップで提供する。

1. ライブラリ部
モジュール	役割	主な型 / 関数
model.rs	ドメインモデル	HoldEvent（保持開始 / 終了 / 重み）
algorithm.rs	スコア計算	calc_score(&[HoldEvent]) -> Result<f64>
重み付き保持秒をそのまま返すシンプル実装（Validation & Error 表現含む）
holdset.rs	ランタイム集計	HoldAggregator …
　• record(&HoldEvent)
　• snapshot() -> Vec<HolderStat>
　• spawn_gc_task(ttl, interval) ✨
内部は dashmap + RwLock、バックグラウンドで TTL 超過レコードを自動削除
metrics.rs	Prometheus 計測	lazy_static! で単一レジストリを公開（record_* 用 Counter / Gauge）
grpc.rs	tonic-gRPC Service	サーバ‐サイド Streaming Broadcast & Stats RPC、serve(addr, aggregator) ヘルパ
bindings.rs	PyO3 バインディング	PyHoldEvent, PyAggregator, calculate_score()（非同期レコードは future_into_py）

アルゴリズム概要
weighted_score ＝ Σ ( (min(end, now) − start).as_secs() × weight )
end が None の場合は “現在時刻” で計算
入力バリデーション：end < start なら Err を返す
f64 で返すため、重みは実数・保持秒は i64 → f64 へ変換

2. バイナリ部
src/main_holdmetrics.rs
サブシステム	詳細
gRPC	0.0.0.0:60051 で待受。HoldMetrics サービスを公開
Prometheus	0.0.0.0:9100/metrics で Text Exposition。prometheus::TextEncoder を毎リクエスト生成
ロギング	tracing_subscriber JSON 出力（環境変数 RUST_LOG 準拠）
Graceful Shutdown	Ctrl-C (tokio::signal::ctrl_c) で両タスクを abort()

3. Python 連携
クラス / 関数	振る舞い	Python 側例
PyHoldEvent	dataclass 的コンストラクタ＋只の getter	ev = PyHoldEvent("tk", "u", 0, None, 1.0)
calculate_score(events)	同期関数	score = calculate_score([ev])
PyAggregator.record(ev)	awaitable（future_into_py）	await agg.record(ev)
PyAggregator.snapshot()	即時 Vec 返却	print(agg.snapshot())

Windows では .dll → .pyd へのコピーが必須。テストユーティリティ ensure_ext_in_path() が対象ディレクトリを sys.path へ inject する。

4. ビルド & 生成物
コンポーネント	ビルド方法
Rust ライブラリ / バイナリ	cargo build --release
Python ホイール	maturin build -m Cargo.toml -o dist/
gRPC Stub (Rust)	build.rs にて tonic_build が hold.proto を OUT_DIR へコンパイル、同時に pb_descriptor.bin を出力し reflection で利用

5. Criterion ベンチ
ベンチ	内容	計測単位
bench_holdmetrics_calc	calc_score 20 000 件	~μs / op
bench_holdmetrics_parallel	HoldAggregator::record を rayon で並列実行	レコード + スナップショット合算時間

6. 依存クレート（抜粋）
tokio 1.x    : 非同期ランタイム
tonic 0.12   : gRPC 実装
prometheus 0.13: メトリクス収集
pyo3 0.25   : Python バインディング
dashmap    : Lock-free Map
criterion / rayon (dev) : ベンチ & 並列化

7. 典型ワークフロー
# 1. gRPC サーバとして起動
cargo run --release --bin main_holdmetrics

# 2. Python から利用
>>> import poh_holdmetrics_rust as hm
>>> agg = hm.PyAggregator()
>>> await agg.record(hm.PyHoldEvent("tk","u",0,None,1.0))
>>> agg.snapshot()
[('u', 12345.0)]

# 3. Prometheus で scrape
curl http://localhost:9100/metrics
まとめ
poh_holdmetrics_rust は 計測 → 集計 → エクスポート の一連を
“Rust の高速性 / マルチスレッド” と “Python からの手軽な呼び出し” の両方で実現するオールインワン実装です。
他サービスからは gRPC、監視系からは Prometheus、データサイエンティストからは Python…という多面的統合が最大の特徴になっています。


# 追加された主な機能
関数/構造体	役割
HolderState	DashMap 内部値。HoldStat への変換実装済み
with_ttl(ttl_secs)	TTL を指定して HoldAggregator を構築
run_gc_once()	TTL 期限切れレコードを即時削除
spawn_gc_task(interval)	Tokio で定期 GC を自動実行する背景タスク生成
top_n(n)	スコア降順ソートで上位 N 件を返却
metrics::HOLD_SCORE_HISTO.observe()	各登録でヒストグラムを更新

これで 高スループット集計／可観測性／自動 GC／ランキング抽出 まで一通りカバーした
“コアロジック” が完成です。


# もしまだ落ちる場合のセルフテスト
・ 生成 so が libpython とリンクしていないか?
readelf -d target/release/libpoh_holdmetrics_rust.so | grep NEEDED
 → libpython… が出てこなければ OK

・ Cargo features が正しく効いているか?
cargo tree -e features | grep pyo3
 → `pyo3 v0.25.1 (features: abi3-py37, extension-module)` のみが出れば OK

ビルド手順
🚀 ビルドコマンド最終版
✅ Python wheel ビルド
maturin build --release --no-default-features --features python

   Compiling chrono v0.4.41
   Compiling pyo3-async-runtimes v0.25.0
warning: `poh_holdmetrics_rust` (build script) generated 1 warning
    Finished `release` profile [optimized] target(s) in 7m 55s
📦 Built wheel for abi3 Python ≥ 3.12 to /mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_rust/target/wheels/poh_holdmetrics_rust-0.1.0-cp312-abi3-manylinux_2_34_x86_64.whl

✅ Rust CLI ビルド
cargo build --release --features core

   Compiling pyo3-macros v0.25.1
warning: `poh_holdmetrics_rust` (build script) generated 1 warning
   Compiling pyo3-async-runtimes v0.25.0
    Finished `release` profile [optimized] target(s) in 2m 23s


# cargoテスト
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust>cargo update -p hyper -p prometheus
    Updating crates.io index
     Locking 0 packages to latest compatible versions
note: pass `--verbose` to see 13 unchanged dependencies behind latest

✅ cargo test は
cargo test --features test

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust>cargo test
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
    Blocking waiting for file lock on package cache
warning: use of deprecated method `tonic_build::Builder::compile`: renamed to `compile_protos()`
  --> build.rs:13:10
   |
13 |         .compile(
   |          ^^^^^^^
   |
   = note: `#[warn(deprecated)]` on by default

warning: `poh_holdmetrics_rust` (build script) generated 1 warning
   Compiling poh_holdmetrics_rust v0.1.0 (D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust)
warning: unused import: `ServerTlsConfig`
  --> src\grpc.rs:10:25
   |
10 |     transport::{Server, ServerTlsConfig},
   |                         ^^^^^^^^^^^^^^^
   |
   = note: `#[warn(unused_imports)]` on by default

warning: `poh_holdmetrics_rust` (lib test) generated 1 warning (1 duplicate)
warning: `poh_holdmetrics_rust` (lib) generated 1 warning (run `cargo fix --lib -p poh_holdmetrics_rust` to apply 1 suggestion)
    Finished `test` profile [unoptimized + debuginfo] target(s) in 4m 53s
     Running unittests src\lib.rs (target\debug\deps\poh_holdmetrics_rust-e44b7db5805b70dd.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src\main_holdmetrics.rs (target\debug\deps\main_holdmetrics-805fec12e9abedff.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_cli.rs (target\debug\deps\test_cli-101d824ca55c9a5d.exe)

running 1 test
test cli_runs_ok ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.76s

     Running tests\test_grpc.rs (target\debug\deps\test_grpc-51d0f18d3193914f.exe)

running 1 test
test grpc_broadcast_roundtrip ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.52s

     Running tests\test_holdmetrics.rs (target\debug\deps\test_holdmetrics-9ee06ea5d645a759.exe)

running 3 tests
test aggregator_accumulates ... ok
test score_basic_weight ... ok
test score_empty_is_zero ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_import.rs (target\debug\deps\test_import-22994746d8b94f1f.exe)

running 1 test
test crate_imports ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_metrics.rs (target\debug\deps\test_metrics-ac15758f13f278de.exe)

running 1 test
test prometheus_metrics_exist ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_py_bindings.rs (target\debug\deps\test_py_bindings-d8f0a8aaed3b55f9.exe)

running 2 tests
test python_calculate_score ... ok
test python_aggregator_flow ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 3.62s

   Doc-tests poh_holdmetrics_rust

running 1 test
test src\holdset.rs - holdset::HoldAggregator::spawn_gc_task (line 147) - compile ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 11.54s


# benches 
# bench-holdmetrics-calc
    Finished `bench` profile [optimized] target(s) in 5m 39s
     Running benches\bench_holdmetrics_calc.rs (target\release\deps\bench_holdmetrics_calc-ef2b3aa4497112b4.exe)
Gnuplot not found, using plotters backend
calc_score 20k events   time:   [966.72 µs 1.0277 ms 1.0859 ms]
Found 24 outliers among 100 measurements (24.00%)
  10 (10.00%) low severe
  10 (10.00%) low mild
  2 (2.00%) high mild
  2 (2.00%) high severe

# bench-holdmetrics-paralles
   Finished `bench` profile [optimized] target(s) in 11.87s
     Running benches\bench_holdmetrics_parallel.rs (target\release\deps\bench_holdmetrics_parallel-34f5ccfda9a0c53d.exe)
Gnuplot not found, using plotters backend
record() × 20k (rayon) time:   [10.587 ms 11.134 ms 11.687 ms]
