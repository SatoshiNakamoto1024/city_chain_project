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
│   │   ├── model.rs                            ← Shared data structures
│   │   ├── metrics.rs                           ← Prometheus gauge ・ counter initialisation
│   │   ├── error.rs                             ← `thiserror::Error` 共通エラー
│   │   ├── bindings.rs                          ← `#[pymodule]`・`#[pyfunction]` PyO3 ラッパ
│   │   └── main_holdmetrics.rs                  ← `--bin main_holdmetrics` CLI デモ
│   └── tests/
│       ├── test_cli.rs
│       ├── test_import.rs
│       ├── test_embed.rs
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
        ├── storage/                               
        │   ├── immudb.py
        │   └── mongodb.py
        │
        └── tests/                                   ← pytest & pytest-asyncio
            ├── __init__.py
            ├── test_tracker.py
            ├── test_calculator.py
            ├── test_scheduler.py
            ├── test_storage.py
            └── test_api.py


“PoH Hold Metrics” とは？
目的	“Proof‑of‑Hold” を数値化するためのミドルウェア
想定ユース	DEX／NFT プロジェクトなどで「保有量 × 保有期間」を KPI にしたいときに
– 書き込み: 各ウォレットが「保有開始/終了イベント」を送信
– 読み出し: リーダーボードやエアドロ判定でスコアを参照
特徴	* Python & Rust の二層構造 – どちらか一方だけでも動く／同じ API
* gRPC ストリーム で高スループット ingest
* MongoDB or インメモリ：本番・テストを自動切替
* 重複区間の除外 などややこしい時間集計をユーティリティに封じ込め

1. コンポーネント全体図
                    +-------------------------------+
                    |  (optional) Rust gRPC server  |  ← bin/main_holdmetrics
┌────────────┐      |      (tonic + tokio)         |
│  dApp /     │ ───►|  Broadcast / Record / Stats  |
│  Client     │     +-------------------------------+
└────────────┘                 │ gRPC (protobuf)
                               ▼
        +-------------------------------------------+
        | AsyncTracker (Python) / HoldAggregator(Rs)|  ← 重複期間をマージしつつメモリ加算
        +---------------------┬---------------------+
                              │ bulk flush (task)
                              ▼
        +-------------------------------------------+
        | MongoStorage (motor) ↔ mongomock fallback |
        |   - hold_events コレクション             |
        |   - $group 集計で Holder ごとにスコア      |
        +-------------------------------------------+

2. Python 実装 (poh_holdmetrics_python)
ファイル	役割
data_models.py	HoldEvent / HoldStat を Pydantic で定義。model_dump が Rust ↔ Python の橋渡し。
calculator.py	calculate_score(events)
  ∑ (duration × weight) を秒単位で返す。重複検出ロジックはここ。
tracker.py	AsyncTracker
  – 一件ずつ record() → メモリ内でホルダー別に 重複マージ
  – snapshot() → 最新 HoldStat をリストで返す。
storage/mongodb.py	motor 非同期クライアント。
  – env 変数で URL/DB を読込み
  – 接続失敗時は mongomock に自動フォールバック
  – $aggregate でスコアを計算。
scheduler.py	（例）10 秒ごとに Tracker → Mongo へ flush するバックグラウンドタスク。
tests/	pytest のユニット／統合テスト（Rust 拡張が入っていると比較テストが追加で走る）。

Python‑only で何ができる？
単体利用 – 依存は純 Python＋Mongo だけなので WSL や Lambda でもすぐ動く。
速度は Rust に劣るが、小規模 (< 数千 TPS) なら十分。

3. Rust 実装 (poh_holdmetrics_rust)
ディレクトリ	主なモジュール	概要
src/grpc.rs	GrpcSvc	tonic で生成した HoldMetrics サービスを実装
  – 双方向ストリーム Broadcast
  – 単発 Record
  – サーバ側ストリーム Stats
src/holdset.rs	HoldAggregator	Arc<DashMap> でスレッド安全なインメモリ集計。
重複除去ロジックは Python と同等だが rayon で並列化。
src/lib.rs	PyO3 でエクスポート	#[pyfunction] calculate_score()
aggregate_events() などを Python から呼べる。
build.rs	tonic-build	hold.proto をビルドして pb モジュール生成。
Cargo.toml	features = ["python"] を付けると cdylib ビルドと extension‑module の両立。	

Rust を入れるメリット
スループット：約 10〜15 倍（rayon + no‑GIL）
gRPC サーバ を単体で常駐させたいときに Python 依存ゼロ。
Python からも同じ API で呼べる（import poh_holdmetrics_rs）。

4. Python × Rust のハイブリッド動作
import 時に try/except
try:
    import poh_holdmetrics_rs as hrs
except ModuleNotFoundError:
    hrs = None
Rust 拡張が在れば
calculate_score = hrs.calculate_score に上書き ⇒ 自動高速化。

無ければそのまま純 Python 実装を使う。
→ 依存を強制しないデザイン。

5. Mongo フォールバックの流れ
MongoStorage.__init__()
 ├─ _create_client()
 │    try:
 │       PyMongo(1.5s) で ping
 │       → 成功: motor.Client を返す
 │    except:
 │       mongomock が import 済なら
 │       → in‑memory Mongo として動作 (_is_mock = True)
 │
 └─ _ensure_indexes() を fire‑and‑forget
テストでは MONGODB_URL を不正値にしても
store._is_mock is True になることを確認します。

6. 代表的なユースケース
シーン	使い方
PoS / エアドロ判定	gRPC Broadcast で大量イベントを Push → get_stats() で重み付き保有時間を取得しランキング。
Web ダッシュボード	Rust gRPC サーバ + Prometheus exporter で Grafana 表示。
オフチェーン計算	Python だけで calculate_score(events) を Jupyter から実験。
ローカル CI	mongomock でテスト → Mongo が無い環境でも OK。

7. まとめ
同じビジネスロジックを Python と Rust に二重実装
– 小回り重視の Python、スピード/常駐サーバは Rust。
インターフェースは完全互換（protobuf / Pydantic モデル）。
自動最適化：Rust 拡張が入っていれば速い方を勝手に使う。
耐障害性：Mongo 死んでもメモリ上で動き続け、再接続可。
これが poh_holdmetrics プロジェクト全体の機能・構造です。


python から pyo3/auto-initialize を外すのが根治策。
[features]
# 拡張モジュールは auto-initialize を絶対入れない
python = ["pyo3/extension-module", "pyo3/abi3-py312"]
python-ext = ["pyo3/extension-module", "pyo3/abi3-py312"]
# 埋め込み専用はこっち
python-embed = ["pyo3/auto-initialize"]
こうしておくと、間違って python でビルドしても安全になる。

使い方
# Rust 拡張ビルド & インストール (maturin 必要)
cd poh_holdmetrics_rust
maturin develop  # or maturin build && pip install dist/*.whl

# Python 側依存
pip install -e ./poh_holdmetrics_python[dev]

# 統合テスト実行
pytest -q libs/algorithm/poh_holdmetrics/test_poh_holdmetrics_integration.py
Rust 拡張が見つからなければスキップ (@pytest.mark.skipif) されるので
Python 単独 CI でも fail しません。

(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics$ pytest -v tes
t_poh_holdmetrics_integration.py
============================================= test session starts ==============================================
platform linux -- Python 3.12.3, pytest-8.4.1, pluggy-1.6.0 -- /home/satoshi/envs/linux-dev/bin/python3.12      
cachedir: .pytest_cache
rootdir: /mnt/d/city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, cov-6.2.1, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 4 items

test_poh_holdmetrics_integration.py::test_calculator_python_vs_rust PASSED                               [ 25%] 
test_poh_holdmetrics_integration.py::test_pipeline_python_vs_rust PASSED                                 [ 50%]
test_poh_holdmetrics_integration.py::test_mongomock_fallback SKIPPED (本番運用では mongomock フォー...)  [ 75%] 
test_poh_holdmetrics_integration.py::test_tracker_overlap_merge PASSED                                   [100%] 

=============================================== warnings summary ===============================================
DAGs/libs/algorithm/poh_holdmetrics/test_poh_holdmetrics_integration.py::test_tracker_overlap_merge
  DAGs/libs/algorithm/poh_holdmetrics/test_poh_holdmetrics_integration.py:166: PytestWarning: The test <Function test_tracker_overlap_merge> is marked with '@pytest.mark.asyncio' but it is not an async function. Please remove the asyncio mark. If the test is not marked explicitly, check for global marks applied via 'pytestmark'.      

DAGs/libs/algorithm/poh_holdmetrics/test_poh_holdmetrics_integration.py::test_tracker_overlap_merge
DAGs/libs/algorithm/poh_holdmetrics/test_poh_holdmetrics_integration.py::test_tracker_overlap_merge
  /mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python/poh_holdmetrics/calculator.py:79: PydanticDeprecatedSince211: Accessing the 'model_fields' attribute on the instance is deprecated. Instead, you should access this attribute from the model class. Deprecated in Pydantic V2.11 to be removed in V3.0.  
    kwargs.update(dict(zip(self.model_fields, args)))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=================================== 3 passed, 1 skipped, 3 warnings in 1.81s ===================================
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics$ 


# 世界統一の両立パターン！
OK、その前提（クレートは1個、Cargo.toml も1個、でも 「Python→Rust」と「Rust→Python」の両方やる）で正規パターンをまとめるね。ポイントは：
同一プロセスの中で、同じクレートを「rlib と cdylib（.pyd）」の両方で同時に使わない。
これさえ守れば、1クレートでも両モードは両立できる。

正規のやり方（1クレートで両立）
1) Cargo.toml：機能フラグを2つに分ける（同時ONしない運用）
[package]
name = "holdmetrics"
version = "0.1.0"
edition = "2021"

[lib]
# rlib と cdylib の両方をビルドできる形で置いておく
crate-type = ["rlib", "cdylib"]
path = "src/lib.rs"

[[bin]]
name = "main_holdmetrics"
path = "src/main_holdmetrics.rs"

[features]
# Python拡張（.pyd/.so）として使う時：auto-initialize は付けない
Python拡張(.pyd) 用（Python→Rust）。auto-initialize なし。
py-ext   = ["pyo3/extension-module"]

# Rust が Python を“埋め込む”時：auto-initialize はこっちにだけ付ける
RustがCPythonを埋め込む 用（Rust→Python）。auto-initialize あり。
py-embed = ["pyo3/auto-initialize"]
default = []  # 明示的に選ぶ

[dependencies]
pyo3 = { version = "0.25", default-features = false }
# ほか依存…

[dev-dependencies]
# ⚠ devでも auto-initialize は付けない（混乱の元）
pyo3 = { version = "0.25", default-features = false }
assert_cmd = "2"
ルール：--features py-ext と --features py-embed を同時に有効化しない（CIでもガード）。
crate-type は両方並べてOK。問題は「実行時に同時ロードしない」こと。

2) ソース構成（同一クレートの中で場合分け）
src/
├─ lib.rs          # コアロジック（PyO3抜き）＋ フィーチャ分岐の窓口
├─ core.rs         # ビジネスロジック（純Rust）
├─ bindings.rs        # #[pymodule]（py-ext の時だけコンパイル）
└─ main_holdmetrics.rs  # 埋め込み起動（py-embed の時だけ意味あり）

src/lib.rs
pub mod core;  // ← 純Rustロジック（両モード共通）
#[cfg(feature = "py-ext")]
mod pyext;
#[cfg(feature = "py-ext")]
pub use pyext::*;  // #[pymodule] などを公開（拡張モジュール用）

src/pyext.rs（拡張モジュール）
#[cfg(feature = "py-ext")]
use pyo3::prelude::*;

#[cfg(feature = "py-ext")]
#[pyfunction]
fn calculate_score(/* ... */) -> f64 { /* core を呼ぶ */ }

#[cfg(feature = "py-ext")]
#[pymodule]
fn poh_holdmetrics_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyHoldEvent>()?;
    m.add_class::<PyAggregator>()?;
    m.add_function(wrap_pyfunction!(calculate_score, m)?)?;
    Ok(())
}
ここに auto-initialize は絶対に入れない。拡張は “外部Pythonが初期化するもの”。

src/main_holdmetrics.rs（埋め込み起動）
#[cfg(feature = "py-embed")]
use pyo3::prelude::*;

fn main() -> anyhow::Result<()> {
    #[cfg(feature = "py-embed")]
    Python::with_gil(|py| -> PyResult<()> {
        // 例：純Pythonコード（パッケージ）を実行する
        // ※ ここで holdmetrics（拡張 .pyd）は import しないのが正解
        let sys = py.import("sys")?;
        sys.getattr("path")?.call_method1("insert", (0, "./python_pkg",))?;
        let app = py.import("holdmetrics_app")?;
        app.call_method0("bootstrap")?;
        Ok(())
    })?;
    Ok(())
}
埋め込み側では、**pure Python（.py）**を動かす。
拡張モジュール（.pyd）を同プロセスで import しないのが鉄則。
（同じクレートを rlib と cdylib の両方で同時ロード＝クラッシュ源）

3) 使い方・コマンド
A. 「Python→Rust」（拡張モジュールとして）
# venv 作成
python -m venv .venv
.venv/Scripts/pip install -U maturin pytest

# .pyd を venv にインストール（auto-initなし）
maturin develop --release --features py-ext

# テスト（pytest推奨）
あなたの理解もOK：
Rust単独 → 既存の Rust テスト一式（test_py_bindings.rs 以外）
Rust→Python（埋め込み）→ test_embed.rs（今回提示）
Python→Rust（拡張）→ test_py_bindings.rs（サブプロセスで python を起動する方式）

/ tests/test_py_bindings.rs：拡張 .pyd の import は常にサブプロセスで
（＝テスト実行プロセスに rlib と .pyd を同時ロードしない）
in-proc（Python::with_gil）で import していた python_calculate_score もサブプロセス実行に変更
PATH いじり、add_dll_directory などの埋め込み用小細工を全部削除（外部の python.exe に任せる）
find_pyd() は venv の site-packages 直下も探すように修正（maturin の配置は直下がデフォルト）

.venv/Scripts/pytest -q
Rust 側からテストするときは 同一プロセスで import しない。
するなら assert_cmdで “外部の python.exe” を起動して -c スクリプトで import する。

B. 「Rust→Python」（埋め込み）
cargo run --release --features py-embed
Windows で配布するなら Embeddable Python を同梱し、PYTHONHOME/PYTHONPATH を設定。
_socket.pyd 等の stdlib C拡張も同梱（asyncio使うなら必須）。

4) テストの切り分け（1クレートのまま）
tests/test_py_bindings.rs（py-ext専用）
→ 中身は assert_cmd で外部 Python を起動して import。
Cargo.toml:
[[test]]
name = "test_py_bindings"
path = "tests/test_py_bindings.rs"
required-features = ["py-ext"]
Rust テストプロセスは 拡張を自分で import しない（= rlib と cdylib の同居を避ける）。

tests/test_embed.rs（py-embed専用）
/venv に拡張を入れる（どちらでも可）
maturin develop --release --features python
→ cargo test --release --features "python-embed" --test test_embed で、埋め込みの起動確認。拡張（.pyd）は import しない。

5) これで両立する理由（正規の設計思想）
1クレートでもOK。ただし
拡張モジュールの世界（py-ext）：Python が主。Rustは cdylib を提供。
埋め込みの世界（py-embed）：Rust が主。Pythonは ランタイムとして内蔵。

この2つを 同プロセスで混ぜようとすると、
同じクレートを rlib と cdylib で二重ロードして AV/GIL Fatal に直行。
→ 実行形態を分けるのが“正規のやり方”。

6) NGパターン（やりがち）
拡張モジュール側に auto-initialize を付ける → Fatal。
Rustテストの同一プロセスで .pyd を import → rlib + cdylib 同居で AV。
DLL を手コピー／PYTHONHOME を雑に上書き → 環境依存クラッシュ。
埋め込みバイナリが 拡張 .pyd を import → ほぼ確実に落ちる。

# コマンドの整理（覚えやすい版）
Rustだけ（gRPC含む・Python不要）
cargo test --release
※あなたの default = ["core","grpc"] なのでこれでOK

Python → Rust（拡張 .pyd のテスト）
先に maturin develop --release --features python（or maturin build）
cargo test --release --features "python grpc"

ここで tests/test_py_bindings.rs は サブプロセスで python を起動するので、rlib と .pyd の衝突は起きません
Rust → Python（埋め込みテスト）
cargo test --release --features "python-embed" --test test_embed -- --nocapture

環境に CPython が見つからなければ skip。
埋め込みでは 自分の .pyd を import しないのがコツ（衝突防止）。

# まとめ
1クレートでOK。
py-ext（拡張）と py-embed（埋め込み）を機能フラグで分岐して、同時に使わない。
拡張は maturin で配り、テストは 外部の python.exe を起動。
埋め込みは pure Python を呼ぶ（拡張を同プロセスで import しない）。
この型が、世界中で最終的に定着してる“正規”の両立パターンだよ。
