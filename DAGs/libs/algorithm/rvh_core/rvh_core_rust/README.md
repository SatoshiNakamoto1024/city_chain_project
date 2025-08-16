rvh_core/                               ← リポジトリ・ルート
├── README.md                      ← プロジェクト概要／ビルド手順
├── LICENSE                        ← Apache-2.0 など
├── .gitignore                     ← target/, __pycache__/ など
├── .github/                       ← CI/CD（後で GitHub Actions 設定を追加）
│   └── workflows/
│       └── ci.yml                 ← cargo test → maturin build → pytest
├── rvh_rust_src/                  ← Rust クレート（pyo3 + CLI）
│   ├── Cargo.toml                 ← crate-type = ["cdylib","rlib","bin"]
│   ├── pyproject.toml             ← maturin 用（wheel ビルド）
│   ├── benches/
│   │   └── bench_hwr_score.rs     ← criterion ベンチマーク
│   ├── examples/
│   │   └── cli_demo.rs            ← cargo run --example cli_demo
│   ├── src/
│   │   ├── lib.rs                 ← pub mod rendezvous; pub mod bindings;
│   │   ├── rendezvous.rs          ← HRW コア + Error 型
│   │   ├── bindings.rs            ← #[pymodule] ec_rust …
│   │   ├── main_rvh.rs            ← 小さな CLI (`cargo run --bin rvh`)
│   │   └── utils.rs               ← 共通ヘルパ（ハッシュ、SIMD 切替など）
│   └── tests/
│       ├── test_rvh_basic.rs      ← HRW 一意性・安定性
│       ├── test_cli.rs            ← CLI encode/decode round-trip
│       └── test_py_bindings.rs    ← pyo3 経由で呼び出し
├── rvh_python/                    ← Python “呼び出し側” パッケージ
│   ├── pyproject.toml             ← [build-system] hatchling / setuptools
│   ├── README.md                  ← pip install rvh_python
│   ├── rvh_python/                ← import rvh_python as rvh
│   │   ├── __init__.py            ← from .vrh_builder import rendezvous_hash
│   │   ├── vrh_builder.py         ← Pure-Py fallback + Rust 呼び出し
│   │   ├── vrh_validator.py       ← 形式チェック／ベンチ補助
│   │   ├── app_rvh.py             ← typer / argparse CLI
│   │   └── _version.py            ← __version__ 自動生成
│   └── tests/
│       ├── test_builder_unit.py   ← Pure-Py 部分テスト
│       └── test_rvh_integration.py← Rust バックエンド有無を切替
├── docs/
│   ├── architecture.md            ← HRW の数式と API 仕様
│   └── ffi_layout.md              ← Python↔Rust 型マップ
└── build.rs                       ← （必要なら）ビルド時生成コード

Rendezvous Hash（別名 HRW Hash）は、「どのノードにデータを割り当てるか」を一義に、かつ安定的（ノードの増減で割り当てが大きく動かない）に決めるアルゴリズムです。以下のポイントで説明します。

1. アルゴリズム概要
キーと各ノード ID を組み合わせてハッシュを計算
各ノードごとに
hash_i = H(node_id || key)
を計算します。ここでは高速かつ強力な Blake2b を使い、その出力の先頭 8～16 バイトを整数（u128）に変換しています。

ハッシュ値をスコアとしてソート
全ノードについて (score, node_id) のペアを作り、score の大きい順にソートします。

上位 k ノードを選出
ソート後の先頭から k 個のノード ID を取り出せば、
「この key に対して責任を持つ k ノード」のリストが得られます。

2. 実装ポイント
ハッシュ関数
blake2::Blake2b（可変長出力版）を用い、
let mut hasher = Blake2b::new();
hasher.update(node.as_bytes());
hasher.update(key.as_bytes());
let hash: GenericArray<u8, _> = hasher.finalize();
で得たバイト列の先頭 16 バイトを u128 にしてスコアとします。

エラー処理
ノードリストが空なら RendezvousError::NoNodes
k > nodes.len() なら RendezvousError::TooMany(k, nodes.len())
として明示的に Result で返します。

公開モジュール化
src/lib.rs に
pub mod rendezvous;
とすることで、外部バイナリ (main_rvh.rs) や他クレートから
use rvh_rust::rendezvous::{rendezvous_hash, RendezvousError};
という形で呼び出し可能になります。

3. 使い方
Cargo パッケージとして取り込み
Cargo.toml に
[dependencies]
rvh_rust = { path = "../rvh_core_rust" }
のように書いてビルドすると…
use rvh_core_rust::rendezvous::{rendezvous_hash, RendezvousError};

fn main() -> Result<(), RendezvousError> {
    let nodes = vec![
        "node-A".to_string(),
        "node-B".to_string(),
        "node-C".to_string(),
    ];
    let key = "transaction-1234";
    let k = 2;

    // 上位 2 ノードを選ぶ
    let selected = rendezvous_hash(&nodes, key, k)?;
    println!("Key `{}` → nodes {:?}", key, selected);

    Ok(())
}

バイナリ（CLI）として
src/main_rvh_core.rs をビルドすると、以下のような CLI が手に入ります。
$ cargo run --bin main_rvh_core -- --help
rvh 0.1.0
Compute Rendezvous Hash (HRW)

USAGE:
    main_rvh [OPTIONS] --nodes <NODES> --key <KEY> --count <COUNT>

OPTIONS:
    -n, --nodes <NODES>      カンマ区切りのノード一覧 (例: node-A,node-B,node-C)
    -k, --key <KEY>          データキー (例: tx-001)
    -c, --count <COUNT>      選出ノード数 k
    -h, --help               ヘルプを表示
    -V, --version            バージョンを表示

これを使って、シェルからも簡単に呼び出せます。
$ main_rvh \
    --nodes node-A,node-B,node-C,node-D \
    --key "user:42" \
    --count 3
Selected nodes for key `user:42`: ["node-C", "node-A", "node-D"]

4. 活用シーン
シャーディング
トランザクションやデータオブジェクトを「どの k ノードに担当させるか」を決定。

ロードバランシング
一意なキーで常に同じノード群にルーティングすることで、キャッシュヒット率やデータ局所性を高める。

ダイナミックノード群
ノード数が変動しても、影響を受けるキーの割り当てが最小限に抑えられる。

以上が「RVH（Rendezvous Hash）」の仕組みと、このライブラリの使い方です。ご不明点や拡張要望があればお知らせください！


Python 側だけで完結させる「Python ネイティブ実装」と、Rust で高速化する「Rust バックエンド実装」を両方用意しておくのが実はベストプラクティスです。

1. なぜ Python だけでもいいケースがあるのか？
計算量
Rendezvous Hash はポイントごとに 1 回のハッシュ（今回は Blake2b）を計算し、ソートして上位 k を取るだけ。ノード数が数十〜数百程度なら Python の hashlib.blake2b＋リストソートで十分高速です。

依存が少ない
純 Python 実装なら C コンパイラや OpenSSL、Blake2b のネイティブライブラリを用意する必要がなく、デプロイが簡単。

可読性
アルゴリズム理解の敷居が低く、メンテナンスしやすい。

2. Rust で実装しておくメリット
大規模ノード群
たとえば数千〜数万ノード、かつ高頻度に何十万回も呼び出すようなシステムでは、Rust 版（Pyo3 経由）が何倍も速い。

メモリ効率
Rust のバッファ再利用／零コスト抽象化で GC 圧力を抑えられる。

一貫したセキュリティ
Blake2b の正確なバイナリ互換と、境界チェックを Rust 側で厳格に担保できる。

# test
# ビルドしたいときは 
PS> cargo build --release

#　dilithium5 を埋め込んだので、python312でのサーバー起動は下記から
# まずはpython312に各種インストール
作業	具体例
3.12のPython.exeを確認	（なければインストール）
D:\Python\Python312\python.exe -m venv D:\city_chain_project\.venv312
作ったあと、
D:\city_chain_project\.venv312\Scripts\activate.bat
という具合に、仮想にはいること。

# .whlを作成する
pythonと同じ仮想環境に入ってから下記をやること
maturin develop --release
maturin build --release -o dist

なぜ必要なのか
pyo3-build-config::add_extension_module_to_path! マクロは 0.21 系に移動した、または非推奨になっており、0.18 系には存在しません。

そこで手動でビルド済みの .so/.dylib/.dll を探し
Windows なら .dll→.pyd にコピー
そのディレクトリを PYTHONPATH に追加
といった処理を行うことで、テスト実行時に Python が拡張モジュールを正しく読み込めるようにします。
これで cargo test → Rust 側全テスト、さらに Python バインディングのテストまで一気通貫でパスするはずです。

#　テストは最後
running 1 test
test test_python_import_only ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.51s

     Running tests\test_py_bindings.rs (target\debug\deps\test_py_bindings-b4a9d95179bb1051.exe)

running 1 test
test python_roundtrip ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s

     Running tests\test_rvh_basic.rs (target\debug\deps\test_rvh_basic-0fcd8a550a6a2ff5.exe)

running 3 tests
test empty_nodes ... ok
test basic_selection ... ok
test k_too_large ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests rvh_core_rust

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

ちょっとした注意
# ベンチを動かすには
cargo bench --bench bench_hrw_score

PyO3 テストは python3-dev/libpython が見つからない環境ではスキップするか、
pyo3/abi3-py310 などビルド済み wheel をインストールしてください。

Cargo.toml には dev-dependencies を追加:
[dev-dependencies]
criterion   = { version = "0.5", features = ["html_reports"] }
assert_cmd  = "2"
predicates  = "3"
pyo3        = { version = "0.18", features = ["auto-initialize"] }
これで rvh_core ライブラリは
ネイティブ API（Rust）
CLI (main_rvh)
Python バインディング（PyO3）
単体テスト / CLI テスト / Py バインディング テスト
Criterion ベンチマーク / CLI デモ
が一通りそろいます。

target/criterion/bench_score_u128/report/index.html
上記にベンチ結果が出力される

warning: `rvh_rust` (bin "main_rvh") generated 1 warning (run `cargo fix --bin "main_rvh"` to apply 1 suggestion)
   Compiling rvh_rust v0.1.0 (D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_rust_src)
    Finished `bench` profile [optimized] target(s) in 1m 54s
     Running benches\bench_hrw_score.rs (target\release\deps\bench_hrw_score-dc4d1415e9cfbbcf.exe)
Gnuplot not found, using plotters backend
score_u128              time:   [331.25 ns 354.12 ns 379.83 ns]
Found 1 outliers among 100 measurements (1.00%)
  1 (1.00%) high mild


# ここから先のおすすめステップ
フェーズ	主な作業	ゴール
1. ベンチ & SIMD 最適化	benches/bench_hrw_score.rs を実行してスコア計算の ns/Op を確認
必要なら blake3 や AVX2/GPU 版へ切り替え	50 ns/Op 以内を目指す
2. Python ラッパ整備	rvh_python/vrh_builder.py でフォールバック実装を wrap
PyPI パッケージ化（maturin build -o wheelhouse）	pip install rvh_rust で即利用
3. DAG Routing 組み込み	dag_routing_rvh クレートから上記関数を呼び出す
ノード除外フィルタと併用して end-to-end ルーティング確認	送信 DAG S1／受信 DAG R2 で動作
4. CI 追加	GitHub Actions に cargo test && pytest を追加	PR 時に自動パス
5. ドキュメント	cargo doc --open で RustDoc、mkdocs gh-pages で Python API docs	OSS 向け公開準備

