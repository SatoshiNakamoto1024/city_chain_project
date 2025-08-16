        └── rust_sending/
            ├── grpc_bridge/            # Rust 用ブリッジ実装
            │   ├── src/
            │   │   ├── lib.rs           # tonic で生成されたサービストレイトを re-export
            │   │   ├── server.rs        # Tonic サーバー実装
            │   │   └── client.rs        # Tonic クライアント・ラッパー
            │   └── proto/               # 同期済み .proto