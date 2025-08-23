下記は “city_chain_project/DAGs” をワークスペースのルートとしたときの
完全版フォルダー構成（Rust + Python 混在、送信 DAG / 受信 DAG / 共通 libs を分離） です。
下表は IO レイヤ（≈130 個想定） の代表フォルダーを
「① sending DAG 専用」「② receiving DAG 専用」「③ 両方で共有」に振り分けたものです。

    ├── io/                             ← **I/O プラグイン (送信専用 / 受信専用 / 共有)**
    │   ├── sending_only/               ← ① 前回答で「sending 専用」とした 11 個
    │   │   ├── io_network_quic/   (2)
    │   │   ├── io_network_multicast/ (2)
    │   │   ├── io_network_nat/   (3)
    │   │   ├── io_message_kafka/ (3)
    │   │   ├── io_message_nats/  (3)
    │   │   ├── io_message_rabbitmq/ (3)
    │   │   ├── io_bench_loadgen/ (1)
    │   │   ├── io_rate_limiter/  (2)
    │   │   ├── io_backpressure/  (2)
    │   │   ├── io_cli_utils/     (1)
    │   │   ├── io_file_transport/ (1)

① sending_DAG でのみ使う I/O フォルダー
フォルダー(スコープ)	役割
io_network_quic (2)	Shard/Broadcast を最速 UDP-QUIC で送出
io_network_multicast (2)	LAN/Broadcast ドメイン向け同報送信
io_network_nat (3)	発信側 NAT 穴あけ／STUN
io_message_kafka (3)	内部 bus へ TxProduced topic を publish
io_message_nats (3)	〃（小規模 SaaS 版）
io_message_rabbitmq (3)	〃（オンプレ版）
io_bench_loadgen (1)	負荷生成・ストレステスト
io_rate_limiter (2)	outbound Shard/s 上限
io_backpressure (2)	gRPC ストリームの Flow-control
io_cli_utils (1)	送信系 CLI サブコマンド補助
io_file_transport (1)	オフライン・ファイルバッチ送信
