DAGs/core (~240)
フォルダー (役割)
dag_structures (2) – Vertex/Edge 型
dag_serde (2) – SerDe
dag_state (2) – 状態機械
dag_executor (2) – WASM 実行
dag_scheduler (2) – tokio 優先度
dag_graph_algo (2) – LCA / reach
dag_topo_sort (2) – 並列 topo sort
dag_gc (2) – GC & pruning
dag_snapshot (2) – Snapshot
dag_checkpoint (2) – CKPT Tx
dag_pruning (2) – Chain Prune
dag_fee_market (1) – 手数料計算
dag_mempool (1) – 未確定 Tx
dag_dedup (2) – Dup 検知 BF
dag_prioritizer (1) – QoS
dag_consensus (2) – 汎用投票
dag_consensus_hotstuff (2)
dag_consensus_abba (2)
dag_consensus_dpos (2)
dag_vote_accel (2) – bitmap
dag_timeout (2) – view 超過
dag_fastpath (2) – fast commit
dag_sharding (2) – shard meta
dag_shard_rs (2)
dag_shard_ldpc (2)
dag_shard_fountain (2)
dag_shard_filter (2)
dag_shard_repair (3) – Repair Worker
dag_shard_zeroize (2)
dag_routing (3) – 送信先選択
dag_routing_rvh (2)
dag_routing_vrf (3)
dag_routing_hvp (2)
dag_clock (2) – HLC Core
dag_clock_skew (1)
dag_poh_mgr (3)
dag_repair_mgr (3)
dag_metrics (2)
dag_security_tls (2)
dag_security_keymgr (2)
dag_security_attest (2)
dag_utils_async (2)
dag_utils_simd (2)
dag_utils_cache (2)
dag_utils_trace (2)
dag_bench (2)
dag_fuzz (2)
dag_mock (1)

③	dag_persistence	永続ストア共通 I/F（選択的に Mongo／immuDB 等へ振り分け）
③	dag_persistence_mongo	MongoDB ドライバ＋BSON SerDe
①	dag_persistence_sqlite	スタンドアロン SQLite ログ保存
②	dag_persistence_parquet	Parquet ⻑期アーカイブ書き込み (arrow + compression)

| ② | dag_consensus_ibft | Istanbul BFT 実装 |
| ② | dag_consensus_qc | Quorum-Cert 集約ロジック単体 |
| ③ | dag_consensus_leader_rotation | VRF ベースのリーダー自動交代 |
| ② | dag_consensus_viewchange | ViewChange FSM (HotStuff 等で共有) |
| ② | dag_consensus_voteacc | Vote Accumulator bitmap 最適化 |
| ② | dag_consensus_cert | Vote→QC→LedgerCert 生成 |
| ③ | dag_consensus_storage | QC/ウォルナットをストレージへ永続化 |
| ① | dag_consensus_tests | シナリオテスト & property-based fuzz |
| ① | dag_consensus_metrics | Prom/OTLP で投票レイテンシ計測 |

| ② | dag_sharding_rs_simd | Reed-Solomon SIMDeez / AVX2 |
| ② | dag_sharding_bloom | Bloom Filter による所在クエリ |
| ② | dag_sharding_cuckoo | Cuckoo Filter 実装 |
| ③ | dag_sharding_locator | Shard → ノード逆引き / Presence cache |

| ③ | dag_routing_kademlia | Kademlia DHT (libp2p) |
| ③ | dag_routing_overlay | Overlay ネット構築ユーティリティ |
| ③ | dag_routing_multicast | UDP / MCAST broad-gossip |
| ③ | dag_routing_floodsub | FloodSub broadcast (libp2p) |
| ③ | dag_routing_quic | QUIC transport (quinn) |
| ③ | dag_routing_libp2p | libp2p Swarm 統合 |

| ② | dag_poh_signature | PoH_ACK Ed25519／Dilithium 署名生成 |
| ② | dag_poh_threshold | t-of-n PoH 集合署名 |
| ① | dag_poh_batcher | ACK を TTL/サイズで区切りバッチ送出 |

| ② | dag_clock_hlc | Hybrid Logical Clock コア |
| ① | dag_clock_ntp | NTP クライアント (chrony API) |
| ① | dag_clock_ptp | PTP ハードウェア時刻同期 |
| ② | dag_clock_lamport | Lamport Clock util |
| ② | dag_clock_vec | Vector Clock util |

| ③ | dag_repair | Repair ルーティング Orchestrator |
| ③ | dag_repair_req | RepairReq 電文組み立て |
| ③ | dag_repair_ack | RepairAck 検証 |
| ② | dag_repair_bulk | Bulk shard download / mmap |
| ③ | dag_repair_throttle | Repair 帯域&同時接続制御 |
| ① | dag_repair_scheduler | asyncio priority queue |
| ① | dag_repair_metrics | Prom counters for repair round |

| ① | dag_tx_pool | Tx メモリプール (async-LRU) |
| ② | dag_tx_filter | RBF／重複／TTL フィルタ |
| ② | dag_tx_validator | 署名検証＋基本ルール |
| ① | dag_tx_fee | 手数料 & ガス上限制御 |
| ① | dag_tx_prioritizer | QoS / tip ベース優先度 |
| ③ | dag_tx_relayer | Tx broadcast scheduler |
| ② | dag_tx_compressor | Snappy / Zstd 圧縮チェーン |

| ② | dag_metrics_prom | Prometheus exporter |
| ① | dag_metrics_otlp | OpenTelemetry OTLP sink |

| ① | dag_monitoring | 監視ツール統合エントリ |
| ① | dag_monitoring_alert | Alertmanager ルール生成 |
| ① | dag_monitoring_dashboard | Grafana JSON Dash 配置 |
| ① | dag_monitoring_tracing | Jaeger / Tempo 配線 |

| ② | dag_security | Security 共通レイヤ |
| ③ | dag_security_mtls | mTLS 証明書の自動更新 (Rust TLS core, Py orchestration) |
| ② | dag_security_vrf_proof | VRF Proof store & verify |
| ② | dag_security_threshold_sig | 閾値署名コア (BLS/Threshold-ECDSA) |
| ② | dag_security_enclave | SGX/SEV enclave bridge |
| ② | dag_security_rand | CSPRNG / HKDF util |

| ② | dag_errors | エラー型・コード定義 (thiserror + anyhow) |
| ① | dag_errors_mapping | REST/gRPC → HTTP Code マッピング |

| ② | dag_utils_bytes | zero-copy bytes util |
| ② | dag_utils_crypto | AES/GF(256)/HKDF helpers |
| ② | dag_utils_rand | Fast RNG / xoshiro |
| ② | dag_utils_hash | Blake3 / SHA3 wrappers |
| ② | dag_utils_heap | bump-arena / slab |
| ① | dag_utils_fs | async-fs helpers |
| ② | dag_utils_retry | exponential back-off |
| ② | dag_utils_backoff | jitter + décor retry |
| ② | dag_utils_compress | gzip / zstd utils |
| ② | dag_utils_stream | Framed stream helpers |
| ② | dag_utils_pool | connection / task pool |
| ② | dag_utils_lru | lock-free LRU cache |
| ② | dag_utils_serde | CBOR / Cap’nP SerDe |
| ③ | dag_utils_quic | QUIC helper functions |
| ② | dag_utils_affinity | CPU core pinning |

| ① | dag_test_vectors | Known-answer tests / golden files |
| ② | dag_benchmarks | Criterion / flamegraph scripts |
| ① | dag_mock | Mock servers & data generators |