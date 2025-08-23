dag_engine_async (2)	Tokio／Rayon を使った DAG 処理ループ（頂点追加→依存解決→実行キュー投入）

ldpc/
├── Cargo.toml
└── src/
    ├── lib.rs
    ├── …                        # ← 既存の gf / design / encoder / decoder など
    │
    ├── pipeline/                # ★ 新規 “非同期パイプライン” レイヤ
    │   ├── mod.rs               # パブリック API と re-export
    │   │
    │   ├── stream_encode.rs     # ▷ ❶ バイト列 → `ShardStream`
    │   ├── stream_decode.rs     # ▷ ❷ `ShardStream` → 完全復元
    │   │
    │   ├── sender/              # 送信側ネット I/O
    │   │   ├── mod.rs
    │   │   ├── quic.rs          # QUIC (quinn) マルチストリーム送信
    │   │   └── tcp.rs           # フォールバック TCP / TLS
    │   │
    │   ├── receiver/            # 受信側ネット I/O
    │   │   ├── mod.rs
    │   │   ├── quic.rs
    │   │   └── tcp.rs
    │   │
    │   └── util.rs              # バッファ pool・CRC32C・BLAKE3 等
    │
    ├── tests/
    │   └── test_pipeline.rs     # End-to-end async ↔︎ network
    └── bench/
        └── bench_pipeline.rs    # Encode+send throughput
    ├── Cargo.toml


5. ビルド手順
# pipeline ディレクトリ直下、あるいはワークスペースルートで
cargo build --features stub-core   # ←デフォルトで入っているので省略可
cargo test  --features stub-core
stub-core が有効なあいだは 本当に符号化はしていません
(1 チャンクを 1 シャードとして送っているだけ)。
ネット I/O／非同期ロジックの動作確認が目的なので十分です。

本物のコアと差し替えるとき
ldpc_core クレートを別途用意（Git submodule でも crates.io でも）

Cargo.toml に
[dependencies]
ldpc_core = { git = "...", branch = "main" }   # など
ビルド時に --no-default-features --features quic のように
stub-core を外すだけで OK。

これで 「まず pipeline だけ動かす」→「あとで本物にリンク」 が
スムーズに行えます。
