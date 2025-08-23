DAGs/algorithm (~150 フォルダー)
フォルダー (役割)
pop (3) – PoP メイン I/F
pop_gps (1) – 逆ジオコード & geopy
pop_polyindex (3) – STRtree 生成 (Rust offset)
pop_cache (1) – LRU キャッシュ
✅ poh_types (1) – 型定義とシリアライズ・基本バリデーション
✅ poh_storage (1) –バイナリファイル保存・SQLiteメタデータ管理・整合性チェック＆リカバリ
✅ poh_ttl (1) – トランザクション「有効期限」設定、期限切れ自動削除
✅ poh_network (1) – PoH トランザクションを多様プロトコル経由で送受信しネットワーク全体に拡散／集約
✅ poh_config (1) – 型安全なDataclass、CLI & ファイルウォッチャを一式提供
✅ poh_metrics (1) – Proof of History用の Prometheus メトリクス収集と HTTP/gRPC 統計の提供
✅ poh_holdmetrics (3) – DEX／NFT プロジェクトなどで「保有量 × 保有期間」を KPI化
✅ poh_request (1) – Pydantic v2 モデル＋nacl 、シンプルな Builder / Sender パターン
✅ poh_ack (3) – 署名 & TTL 検証
✅ poh_batcher (1) – ACK バッチ圧縮
dpos_core (2) – DPoS 投票集計
dpos_weight (1) – ステーク管理
dpos_slash (1) – スラッシング
dpos_election (3) – 代表者ローテ
hotstuff_core (2) – HotStuff 3-phase
hotstuff_qc (2) – Quorum Cert
hotstuff_fast (2) – Fast-path
hotstuff_pacemaker (3) – Pacemaker & Timeout
abba_core (2) – ABBA 本体
abba_reduction (2) – Reduction フェーズ
abba_common_coin (2) – 共通乱数
vrf_bls (2) – BLS-VRF
vrf_libsodium (2) – libsodium VRF
vrf_leader (3) – リーダー選出
✅ rvh_core (3) – HRW スコア
✅ rvh_faultset (3) – ジオハッシュクラスタリング, Rust 製高速フェイルオーバー機能
✅ rvh_trace (3) – `tracing` + `opentelemetry` を使った本格的な Span／イベント発行
✅ rvh_filter (1) – ノード除外
✅ rvh_stable (1) – O(1)・メモリフリー・再配置最小Jump Hash
✅ rvh_simd (2) – SIMD ハッシュ
✅ rvh_weighted (2) - 重み付き HRW ( stake / 容量 / RTT を反映 )
hvp_hyparview (2) – View 管理
hvp_plumtree (2) – Plumtree
hvp_shuffle (2) – シャッフル
ec_rs (2) – RS SIMD
ec_ldpc (2) – LDPC
ec_fountain (2) – RaptorQ
ec_rs_gf16 (2) – GF(16)
ec_rs_gf32 (2) – GF(32)
cbf_bloom (2) – Bloom Filter
cbf_cuckoo (2) – Cuckoo Filter
cbf_xor (2) – XOR Filter
tes_tsig (2) – BLS/Dilithium t-sig
tes_tkem (2) – NTRU-KEM
tes_dkg (2) – DKG
tnh_hlc (2) – HLC 算術
tnh_ntp (1) – NTP Client
tnh_ptp (3) – PTP & HW Timestamp
tnh_drift_detect (1) – ドリフト監視
sc_coord (3) – シャード原子コミット
sc_two_phase (1) – 2PC
sc_xa (1) – XA
sc_retry (1) – 再試行
algo_research_sim (1) – 研究用シム
algo_fuzz (2) – libFuzzer

merkle_tree	②	取引バッチのハッシュ木／簡易 SPV 証明
merkle_mmr	②	Append-only Merkle Mountain Range（永続ログ用）
kzg_commit	②	KZG 多項式コミットメント（データ可用性 & DAS）
zk_snark_groth16	②	Groth16 ZK-SNARK（機密 Tx 証明）
zk_plonk	②	PLONK 汎用 ZK 回路バックエンド
zk_bulletproofs	②	Bulletproofs 範囲証明（Confidential Assets）
vdf_wesolowski	②	Wesolowski VDF（乱数ビーコン／タイムロック）
sss_shamir	②	Shamir Secret-Sharing (n,k) 基盤
crdt_lww	③	LWW-Element-Set CRDT（メタ情報同期）
crdt_delta	③	δ-State-based CRDT（オフライン→再接続）
accumulator_rsa	②	RSA アキュムレータ（メンバーシップ証明）
accumulator_bls	②	BLS ベース定数サイズ証明
ed_signatures	②	Ed25519／Schnorr 汎用署名
mpc_dkg	②	Multi-Party DKG (FROST) 基盤
he_paillier	②	Paillier 準同型暗号ユーティリティ
range_proof_pedersen	②	Pedersen + Bullet-range 証明補助
bandwidth_estimator	③	Gossip 帯域のリアルタイム計測
priority_fair_queue	③	Tx QoS & 公平スケジューラ
anti_entropy_epidemic	③	Anti-entropy push/pull 同期
overlay_chord	②	Chord DHT ルーティング (研究用)
overlay_pastry	②	Pastry/RoutingTable ライブラリ
