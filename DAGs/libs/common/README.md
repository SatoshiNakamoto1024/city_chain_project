DAGs/common (~70)
フォルダー (役割)
common_config_toml (1)
common_config_env (1)
common_error_codes (1)
common_async_retry (1)
common_crypto_bls (2)
common_crypto_dilithium (2)
common_crypto_ntru (2)
common_crypto_aesgcm (2)
common_crypto_hkdf (2)
common_time_human (1)
common_time_rfc3339 (1)
common_utils_hash (2)
common_utils_rand (2)
common_utils_compress (2)
common_utils_pool (2)
common_utils_serde_ext (1)
common_macros_error (2)
common_macros_instrument (2)
common_build_version (2)
common_fuzz_targets (2)
common_test_fixtures (1)

common_config	③	すべての設定ローダー共通 Facade
common_config_toml	③	TOML ホットリロード（serde + tomli）
common_config_json	①	JSON 設定とスキーマ検証
common_config_yaml	①	YAML 互換ローダ
common_config_env	①	ENV_ 変数オーバーレイ
common_config_cli	③	Clap／Typer の CLI-Flag バインド
common_error	③	anyhow / thiserror の共通ラッパ
common_error_codes	③	ECxxxxx 等コード→HTTP ステータス
common_error_macro	②	bail! / ensure! マクロ集
common_async	③	Python asyncio ↔ Tokio ブリッジ
common_async_tokio	②	tokio ランタイム設定プリセット
common_async_runtime	②	single-thread & multithread executors
common_async_channel	②	MPSC / broadcast / bounded ch.
common_async_retry	③	back-off・jitter・idempotent再送
common_async_timeout	②	cancellable timeout ラッパ
common_crypto	③	暗号 API ルート (sign/verify/enc)
common_crypto_dilithium	②	PQ Dilithium 署名実装
common_crypto_ntru	②	PQ NTRU-KEM ラッパ
common_crypto_bls	②	BLS12-381 G1/G2 ops
common_crypto_vrf	②	VRF 汎用ユーティリティ
common_crypto_aead	②	AES-GCM / ChaCha20-Poly1305
common_crypto_mac	②	HMAC / CMAC helpers
common_crypto_rng	②	ChaCha／OS RNG 抽象
common_crypto_utils	②	HKDF・PBKDF 等小物
common_time	③	クロック抽象・sleep/now
common_time_format	①	RFC3339 文字列生成
common_time_parse	①	RFC3339 / epoch パース
common_time_human	①	秒↔h:m:s 変換
common_time_zone	①	tzdb & オフセット計算
common_traits	③	Storage / Consensus 等 super-traits
common_traits_storage	③	get/put/list 汎用トrait
common_traits_network	③	transport 抽象 (send/recv)
common_traits_consensus	③	vote & finalize Trait
common_traits_sharding	③	encode/decode/locate Trait
common_utils	③	bytes・rand・hash 入口
common_utils_bytes	②	zero-copy byte-slice utils
common_utils_hash	②	Blake2／Keccak 汎用
common_utils_rand	②	Thread-safe RNG adapters
common_utils_math	②	GF(256)・modexp 小数演算
common_utils_compress	②	zstd／snappy 包装
common_utils_pool	②	buffer／obj-pool & zero-copy
common_utils_lru	②	lru-cache (clock / shard map)
common_utils_cache	②	TTL & 失効コールバック
common_utils_trace	②	tracing 層共通 helper
common_utils_simd	②	packed_simd 対応 API
common_utils_zeroize	②	secret wipe (zeroize crate)
common_build_info	③	ビルド時 env / cfg 収集
common_build_version	②	Git SHA / semver 埋め込み
common_build_git	②	vergen-style git meta
common_macros	②	再エクスポート用 prelude macro
common_macros_serde	②	derive + serde tweak
common_macros_error	②	前述 bail!/ensure! 等
common_macros_logging	②	log! → tracing bridge