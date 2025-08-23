    │   ├── full_node/                   # ── Level 1: City レイヤ（フルノード）
    │   │   ├── grpc_server.py           # PoH_REQUEST 受信 ⇒ PoH_ACK 返信
    │   │   ├── grpc_client.py           # 他ノードへの gRPC クライアント
    │   │   ├── poh_ack.py               # PoH_ACK 生成・署名
    │   │   ├── shard_manager.py         # 10-way シャーディング + DAG キャッシュ
