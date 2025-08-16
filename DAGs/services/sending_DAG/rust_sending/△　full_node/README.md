        ├── full_node/                  # City レイヤ向け高速並列処理
        │   ├── src/
        │   │   ├── lib.rs               # gRPC サーバ実装
        │   │   ├── poh.rs               # PoH 署名／検証（Dilithium）
        │   │   ├── sharder.rs           # シャーディング・ワーカー
        │   │   └── ntru_kem.rs          # NTRU KEM 包装ロジック