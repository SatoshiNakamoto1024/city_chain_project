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
│   │       ├── test_cli.rs 
│   │       ├── test_py_bindings.rs 
│   │       ├── test_import.rs 
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

以下、rvh_faultset の機能概要と使い方をまとめました。
rvh_faultset は、ジオハッシュによるクラスタリングと Rust 製の高速フェイルオーバー機能を組み合わせ、リージョン単位でのレイテンシ最適化とフェイルオーバー選択を行うパイプラインです。以下、主要機能を詳しく解説します。

1. ジオハッシュによるクラスタリング（純 Python 部分）
Geohash エンコード
from rvh_faultset.geohash import encode
gh = encode(lat, lon, precision)
緯度経度をビット演算で interleave し、Base32 文字列（長さ precision）として返します。

クラスタ分け
from rvh_faultset.geohash import geohash_cluster
clusters = geohash_cluster(nodes, precision)
各ノードを同じジオハッシュ・プレフィックスごとにまとめてリスト化します。たとえば precision=5 なら、半径数十キロ程度の領域ごとに分割されます。

これにより、地理的に近いノード群ごとに独立したフェイルオーバー判定を行えるようになります。

2. Rust バックエンドによる高速フェイルオーバー
同期版フェイルオーバー
from rvh_faultset_rust import failover
survivors: List[str] = failover(ids, latencies, threshold)
ids: List[str] … ノード ID のリスト
latencies: List[float] … 各ノードのレイテンシ（ms）
threshold: float … 残すノードの閾値（この値以下のレイテンシを持つノードだけを返す）
閾値以下のノードをフィルタリングして返し、リストが空になる場合や入力が不正な場合は Python の例外にマッピングされます。

非同期版フェイルオーバー
from rvh_faultset_rust import failover_async
survivors: List[str] = await failover_async(ids, latencies, threshold)
Python の asyncio と連携し、一度だけ初期化される Tokio ランタイム上で実行されます。

await で結果を取得でき、同期呼び出しと同じく高速に動作します。

3. 高レベル Python パイプライン
from rvh_faultset.faultset_builder import faultset, FaultsetError

survivors = faultset(nodes, threshold, precision=6)
入力検証：nodes が空なら即座に FaultsetError("nodes list is empty")

クラスタ分け：ジオハッシュで同じ領域にあるノードをまとめる
各クラスタに対し
ids と latencies を抽出
Rust 実装（failover or failover_async）または純 Python 実装にフォールバック
各クラスタで生き残ったノード ID を集約
全クラスタで例外（誰も残らない）なら最終的に FaultsetError("all clusters yielded no survivors")
結果返却：生き残った全ノード ID のリスト
Rust バックエンドがインストールされていない環境でも動くように、純 Python 実装 _python_failover を内包しています。

4. 同期 vs. 非同期 API
同期：上記 faultset(...) をそのまま呼び出し

非同期：追加で faultset_async(...) を実装予定
survivors = await faultset_async(nodes, threshold, precision)

スクリプトから一発：
import asyncio
survivors = asyncio.run(faultset_async(nodes, ...))

5. CLI ツール
python -m rvh_faultset.app_faultset \
  --nodes "id:lat:lon:latency,..." \
  --threshold 100.0 \
  [--precision 5] [--async] [--level debug]
--nodes：id:lat:lon:latency をカンマ区切りで指定

--threshold：閾値

--precision：ジオハッシュ桁数（デフォルト 5）

--async：非同期版 API を内部で使う

--level：将来のロギングレベル用（現状は受け取るだけ）

6. CI／ベンチマーク
GitHub Actions で Rust の cargo test → maturin ビルド → pytest（Rust/純 Python 両方）→ベンチマーク

Criterion ベンチマーク例で「1,000 ノード failover」や Rayon 並列版との比較ができます。

なぜ使うのか？
リージョン別フェイルオーバー：地理的に近いノードだけで選抜することで、大域的な障害をローカルに閉じ込める。
高速処理：Rust コアで数万ノードでもミリ秒単位で実行可能。
柔軟性：純 Python フォールバックで依存を抑えつつ、Rust を入れれば即座に高速化。
非同期対応：asyncio サービスにシームレス統合。
手軽な CLI：ワンライナーでサバイバー判定ができる。
このように rvh_faultset は、ジオハッシュ＋閾値フィルタによるリージョン単位のフェイルオーバー選択を、使いやすい Python API と Rust のパフォーマンスで提供する、実運用レベルのソリューションです。


# 機能概要
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


#　統合テスト（rvh_faultset_integration.py）
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

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset>pytest -v test_faultset_integration.py
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 8 items

test_faultset_integration.py::test_sync_basic PASSED                                                             [ 12%]
test_faultset_integration.py::test_async_basic PASSED                                                            [ 25%]
test_faultset_integration.py::test_sync_empty PASSED                                                             [ 37%]
test_faultset_integration.py::test_async_empty PASSED                                                            [ 50%]
test_faultset_integration.py::test_sync_all_filtered PASSED                                                      [ 62%]
test_faultset_integration.py::test_async_all_filtered PASSED                                                     [ 75%]
test_faultset_integration.py::test_cli_sync PASSED                                                               [ 87%]
test_faultset_integration.py::test_cli_async PASSED                                                              [100%]

================================================== 8 passed in 1.97s ==================================================


