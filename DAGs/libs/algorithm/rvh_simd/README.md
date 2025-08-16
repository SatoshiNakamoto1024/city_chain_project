rvh_simd (2) – SIMD ハッシュ

以下は Rust 専用 (②) の SIMD 版ハッシュ・クレート rvh_simd の “本番用ひな型” です。
rvh_core と並列で置けば、そのまま cargo bench や上位ライブラリから利用できます。

1️⃣ ディレクトリ・ツリー
rvh_simd/                     # ← リポジトリ or mono-repo 内サブクレート
├── Cargo.toml
├── README.md
├── .gitignore
├── build.rs                  # CPU 拡張命令セットの自動検出
├── src/
│   ├── lib.rs                # 公開エントリポイント
│   ├── simd_hash.rs          # AVX2 / NEON 実装 + フォールバック
│   └── main_simd.rs          # 速度計測 CLI（任意; feature = "cli"）
├── benches/
│   └── bench_simd_hash.rs    # Criterion ベンチ
├── tests/
│   └── test_simd_hash.rs     # 単体テスト
└── .github/
    └── workflows/
        └── ci.yml            # cargo test / bench / clippy

使い方メモ
# ビルド & 単体テスト
cargo test -p rvh_simd

# ベンチ (結果は target/criterion/)
cargo bench -p rvh_simd

# CLI（任意）
cargo run -p rvh_simd --features cli -- -n node1 -k obj123
これで SIMD ハッシュ専用クレート が完成です。
上位の rvh_core ないし DAG 層からは rvh_simd::score_u128_simd() を呼び出すだけで、走行環境に合わせた AVX2 / NEON 最適化が透過的に適用されます。


running 2 tests
test determinism ... ok
test different_inputs ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

   Doc-tests rvh_simd

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


# ベンチを動かすには
cargo bench --bench bench_simd_hash

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_simd>cargo bench --bench bench_simd_hash
   Compiling rvh_simd v0.1.0 (D:\city_chain_project\DAGs\libs\algorithm\rvh_simd)
    Finished `bench` profile [optimized] target(s) in 21.21s
     Running benches\bench_simd_hash.rs (target\release\deps\bench_simd_hash-ec84449a91760ca5.exe)
Gnuplot not found, using plotters backend
score_u128_simd         time:   [94.656 ns 98.290 ns 102.36 ns]
                        change: [-8.2861% -4.8890% -1.2833%] (p = 0.01 < 0.05)
                        Performance has improved.
Found 13 outliers among 100 measurements (13.00%)
  3 (3.00%) high mild
  10 (10.00%) high severe


# 概要
rvh_simd は、Rendezvous Hash（HRW：Highest Random Weight）やフェイルオーバーに必要となる「ノード×オブジェクト」の組み合わせから 128 ビットの重み（スコア）を高速に計算するための Rust クレートです。以下、主な特徴と構成を日本語で詳しく解説します。

1. 背景と目的
Rendezvous Hash では、各ノードとオブジェクトの組み合わせに対して擬似乱数的なスコアを算出し、その最大値を持つノードを「担当ノード」として選出します。
このスコア計算は大量に行われるため、高速化が運用上のボトルネックになりがちです。
そこで rvh_simd では…

SIMD 命令（AVX2／NEON）
マルチコア並列（blake3 の Rayon 機能）
フォールバックとしてのソフトウェア実装
を組み合わせ、CPU の性能を最大限引き出すことで、スコア計算の高速化を実現します。

2. 主な機能
2.1. score_u128_simd(node_id: &str, object_key: &str) -> Result<u128, HashScoreError>
入力
node_id: ノードを一意に識別する文字列
object_key: オブジェクト（キー）を表す文字列

出力
u128: Blake3 ハッシュの上位 128 ビットを Big-Endian で解釈した擬似乱数スコア

エラー
HashScoreError::EmptyNode / HashScoreError::EmptyKey
（いずれかの文字列が空だった場合に返却）

内部では blake3 ライブラリを使っています。blake3 は既に内部で SIMD（AVX2/NEON） やマルチスレッド（Rayon）を生かす設計なので、追加の複雑な分岐は不要です。

2.2. エイリアスと再エクスポート
crate::score128

crate::score_u128_simd

両方の名前で呼び出せるよう、src/lib.rs で再エクスポートしています。

3. コード構成
rvh_simd/
├── Cargo.toml           # 依存関係・ビルド設定
├── build.rs             # ビルド時に CPU の SIMD サポート（avx2, neon）を自動検出
├── src/
│   ├── lib.rs           # 公開 API の定義と再エクスポート
│   ├── simd_hash.rs     # スコア計算ロジック
│   └── main_simd.rs     # （feature="cli"）CLI 実行用バイナリ
├── benches/             # Criterion ベンチマーク
│   └── bench_simd_hash.rs
└── tests/               # ユニットテスト
    └── test_simd_hash.rs

build.rs
std::is_x86_feature_detected!("avx2") / std::is_aarch64_feature_detected!("neon") を使い、コンパイル時に --cfg feature="avx2" / "neon" を自動付与します。

simd_hash.rs
入力検証 → blake3::Hasher でハッシュ → 上位 16 バイトを u128 化

main_simd.rs
clap ベースの小型 CLI。--features cli 指定時にバイナリ main_simd がビルドされ、
$ cargo run --features cli -- -n node1 -k tx42
0x0123456789abcdef0123456789abcdef
といった使い方が可能。

4. ベンチマーク
benches/bench_simd_hash.rs
Criterion を使って score_u128_simd() の高速性を測定。
数千〜数万回のループで平均処理時間を自動レポートします。

5. テスト
tests/test_simd_hash.rs
同じ入力で常に同じ出力（決定性）
入力を変えれば異なる出力
を検証するシンプルなユニットテストを備えています。

6. 依存関係
必須
blake3 (SIMD＋Rayon)
thiserror (エラー型作成)
開発
criterion (ベンチマーク)
assert_cmd / predicates (CLI テスト)
walkdir / serde_json など

7. 実運用イメージ
rvh_faultset や他の RVH パイプラインからこのクレートを呼び出し、ノード・オブジェクトごとの重みを取得

得られたスコアを比較してノード選択・フェイルオーバー

必要に応じて CLI（main_simd）で単体検証・デバッグ

Criterion ベンチでリリースビルド後の性能を継続モニタリング

—— 以上が rvh_simd の全容です。CPU の SIMD 命令＋マルチコアを生かした 128 ビットハッシュスコア生成ライブラリとして、Rendezvous Hash やフェイルオーバーのコア処理を劇的に高速化します。


＃　WSLでもcargo build したい
# 1. Rust ツールチェーンを入れる
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# 2. PATH を通す（新しいシェルを開くか、今のシェルで）
source $HOME/.cargo/env     # ~/.bashrc にも自動追記されるはず

# 3. 動作確認
cargo --version   # => cargo 1.79.0 (例)
rustc --version   # => rustc 1.79.0

その後のビルド
cd /mnt/d/city_chain_project/DAGs/libs/algorithm/rvh_simd
cargo build --release
これで WSL 側でも cargo が動き、
Windows と WSL の両方で開発・テストが出来るようになります。