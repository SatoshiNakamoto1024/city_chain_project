# test_configs.rs について
test_configs.rs のテストを動かすために最低限必要なのは、以下のファイルです。

src/config.toml
– テスト対象となる設定フォーマットのサンプル。

src/configs.rs
– Config 構造体の定義、config.toml からの読み込み・パース・バリデーション・デフォルト値注入ロジック。

src/lib.rs
– pub mod configs; で configs.rs を公開し、テストから crate::configs::Config が使えるようにします。

Cargo.toml
– serde, toml, thiserror など、configs.rs が依存するクレートを宣言しておく必要があります。

tests/test_configs.rs
– すでにお持ちのテストファイル。crate::configs::load_config() などを呼び出します。

具体的に関係するファイル
ec_rust_src/
├── Cargo.toml                  ← serde, toml, thiserror の宣言を確認
├── src/
│   ├── lib.rs                  ← pub mod configs;
│   ├── config.toml             ← サンプル設定ファイル
│   └── configs.rs              ← Config の実装
└── tests/
    └── test_configs.rs         ← 実際に走らせるテスト

１．Cargo.toml に依存を追加
[dependencies]
serde = { version = "1.0", features = ["derive"] }
toml = "0.7"
thiserror = "1.0"

２．src/lib.rs
pub mod configs;

３．src/config.toml
# デフォルト設定の例
[data]
shard_size = 1024
data_shards = 10
parity_shards = 4

[storage]
retention_days = 180
replication = "continental"

[performance]
timeout_ms = 500

４．src/configs.rs

この４つさえ整えば、cargo test -- --test test_configs で設定周りのテストだけを最初にパスできます。
