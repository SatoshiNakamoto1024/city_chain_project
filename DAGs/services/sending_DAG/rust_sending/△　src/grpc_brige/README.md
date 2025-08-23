        └── rust_sending/
            ├── grpc_bridge/            # Rust 用ブリッジ実装
            │   ├── src/
            │   │   ├── lib.rs           # tonic で生成されたサービストレイトを re-export
            │   │   ├── server.rs        # Tonic サーバー実装
            │   │   └── client.rs        # Tonic クライアント・ラッパー
            │   └── proto/               # 同期済み .proto

rust_sending/grpc_bridge/src/lib.rs
tonic::include_proto!("common.grpc_dag"); などで生成コードを取り込む。


# プロジェクトルートに grpc_bridge 用のビルドスクリプトを追加：
  注意！まだ追加していないので、実装時に追加して！

.PHONY: grpc-gen-py grpc-gen-rs

grpc-gen-py:
    python -m grpc_tools.protoc \
      -I network/python/common/grpc_bridge/proto \
      --python_out=network/python/common/grpc_bridge/gen \
      --grpc_python_out=network/python/common/grpc_bridge/gen \
      network/python/common/grpc_bridge/proto/dag.proto

grpc-gen-rs:
    protoc \
      --proto_path=network/python/common/grpc_bridge/proto \
      --rust_out=network/sending_DAG/rust_sending/grpc_bridge/src \
      --grpc_out=network/sending_DAG/rust_sending/grpc_bridge/src \
      --plugin=protoc-gen-grpc=`which grpc_rust_plugin` \
      network/python/common/grpc_bridge/proto/dag.proto
