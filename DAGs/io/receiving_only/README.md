下記は “city_chain_project/DAGs” をワークスペースのルートとしたときの
完全版フォルダー構成（Rust + Python 混在、送信 DAG / 受信 DAG / 共通 libs を分離） です。
下表は IO レイヤ（≈130 個想定） の代表フォルダーを
「① sending DAG 専用」「② receiving DAG 専用」「③ 両方で共有」に振り分けたものです。

    ├── io/                             ← **I/O プラグイン (送信専用 / 受信専用 / 共有)**
│   ├── receiving_only/             ← ② 受信専用 8 個
    │   │   ├── io_network_libp2p/ (2)
    │   │   ├── io_network_kademlia/ (2)
    │   │   ├── io_storage_mongo/  (3)
    │   │   ├── io_storage_rocksdb/ (2)
    │   │   ├── io_storage_sqlite/ (1)
    │   │   ├── io_storage_parquet/ (1)
    │   │   ├── io_storage_backup/ (1)
    │   │   ├── io_sim_netloss/    (1)

② receiving_DAG でのみ使う I/O フォルダー
フォルダー(スコープ)	役割
io_network_libp2p (2)	shard 受信 P2P オーバレイ
io_network_kademlia (2)	missing-shard DHT ルックアップ
io_storage_mongo (3)	完了 Tx を 6 か月保存
io_storage_rocksdb (2)	一時キュー / Repair バッファ
io_storage_sqlite (1)	Edge-node キャッシュ
io_storage_parquet (1)	ETL 用スキャンフレンドリ転置ファイル
io_storage_backup (1)	受信側 DB オフサイトバックアップ
io_sim_netloss (1)	ネットワーク障害シミュレーション（復元試験）
