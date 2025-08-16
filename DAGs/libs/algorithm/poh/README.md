以下のように３種類に分けるのが自然です。

① Python-only クレート
（軽量なロジック／I/O／スケジューリング周りなど。Rust 側に伝搬せず、純粋に Python で完結）

poh_types
Transaction や PoH_ACK／REQ のデータ構造定義だけを持つ

poh_storage
オリジナル Tx のローカル保存、SHA-256 ハッシュ計算、SQLite／ファイル I/O、起動時リカバリ

poh_ttl
TTL 管理とガベージコレクション。asyncio タスクで定期スキャン＆自動削除

poh_network
gRPC／HTTP／UDP 経由の PoH Tx ブロードキャスト受信、ピア管理、asyncio.gather

poh_config
TOML/JSON/YAML 形式の設定読み込み (MIN_POH_REQUIRED, TTL_SECONDS など)

poh_metrics
Prometheus エクスポーター／メトリクス登録（PoH 発行数、検証成功率、GC 件数 など）

poh_request
PoH_REQUEST Tx の組み立てテンプレート & 送信ラッパ

poh_batcher
バッチ処理（PoH_ACK をまとめて送る／受ける）

② Rust-only クレート
（極めて高性能に実装したいコア部分だけを Rust で。Python からは FFI／PyO3 経由で呼び出す想定）

poh_crypto
Dilithium3／Ed25519 署名生成・検証、ペイロード（tx_id‖storage_hash‖timestamp）処理のみ

③ ハイブリッド（PyO3 でつなぐ）クレート
（Python の上位ロジックから Rust のコア機能だけを抜き出して呼び出す）

poh_builder

build_poh_request(tx_id)

build_poh_ack(tx_id, storage_hash)
（内部で poh_crypto の署名生成を行い、戻り値を Python に返す）

poh_ack
PoH_ACK Tx の受信時検証／Python 側へのデシリアライズ
（poh_crypto の検証関数を呼び出す）

poh_validator
PoH_ACK の署名検証＋カウント閾値チェック（count_poh_and_check(min_required)）

poh_repair
REPAIR_REQ／REPAIR_ACK Tx の組み立て・送受信・検証
（REQ は Python で作り、ACK の検証は Rust コアで）

全体像イメージ
poh_core (meta-crate)
├─ poh_types         # Python-only
├─ poh_storage       # Python-only
├─ poh_ttl           # Python-only
├─ poh_network       # Python-only
├─ poh_config        # Python-only
├─ poh_metrics       # Python-only
├─ poh_request       # Python-only
├─ poh_batcher       # Python-only
├─ poh_builder       # hybrid (PyO3 → poh_crypto.sign)
├─ poh_ack           # hybrid (PyO3 → poh_crypto.verify)
├─ poh_repair        # hybrid (PyO3 → poh_crypto.verify)
└─ poh_cli           # Python-only entry point, 各サブコマンド束ねる

これで、
Python-only で書きたいところは完全に Python
Rust-only で超速・安全に書きたい署名ロジックは Rust
ハイブリッド は PyO3 で橋渡しして、Python 上の非同期フローから呼び出せる
という、各モジュールが最適な言語で実装されるモノリスにならず、かつ相互依存も最小限にしたクレート構成になります。



PoH 周りの機能をそれぞれ独立した“クレート”（Rust でいうところのパッケージ／Python でいうところのモジュール・サブパッケージ）に分けると、最低でもこんな構成になります。

poh_types
└── PoH Tx（ACK／REQ）や内部メッセージの共通データ構造を定義
tx_id, holder_id, timestamp, storage_hash, sig_alg, signature など

poh_storage
└── オリジナル Tx のローカル保存・ハッシュ計算・永続化
SHA-256 ハッシュ, SQLite/LevelDB/ファイル I/O, 起動時リカバリ

poh_ttl
└── PoH_ACK／オリジナルデータの TTL 管理＆ガベージコレクション
asyncio タスクで定期スキャン & 自動削除

poh_builder
└── PoH_REQUEST／PoH_ACK Tx の組み立て
build_poh_request(tx_id) / build_poh_ack(tx_id, storage_hash)

poh_network
└── gRPC／HTTP／UDP を使った PoH Tx のブロードキャストと受信
ピア管理、並列送信 (asyncio.gather)

poh_repair
└── TTL 切れや未達データの再取得（REPAIR_REQ/ACK）の生成・送受信・検証

poh_config
└── TOML/JSON/YAML 形式の設定読み込み
MIN_POH_REQUIRED, BROADCAST_PEERS, TTL_SECONDS など

poh_metrics
└── Prometheus などへのメトリクス公開
発行数、検証成功率、再送回数、TTL GC 件数 など

こう分割すると、
再利用性：たとえば poh_crypto は別の署名ワークフローでも流用可
独立テスト：Storage 周りだけ、Network 周りだけ、とユニット／結合テストが書きやすい
明確な依存関係：上流の poh_builder → poh_crypto → poh_storage など
というメリットがあります。全体をラップするメタクレート poh を用意して、各サブクレートを再エクスポートしてもよいでしょう。



お疲れさまです！現状の１０クレートで PoH-ACK 周りからメトリクス、設定、永続化、バッチ処理までほぼ一通りカバーできています。ただ、実運用／運用支援まで踏み込むと、以下のような「補助的だけどあると便利」なクレートを追加検討するとさらに抜け漏れがなくなります。

追加で検討したいクレート群
クレート名	タイプ	主な責務
poh_cli	(1)	各種操作をまとめたコマンドラインインターフェイス（poh init / poh status / poh send など）
poh_rpc	(3)	gRPC／REST サーバ・クライアント実装。PoH ノードへのリクエスト送受信をプロトコル定義から自動生成
poh_indexer	(2)	履歴データを効率的に検索できるオンディスク・インデクサー（時刻帯検索、スロット範囲検索など）
poh_validator	(3)	バリデータセットの管理・フェイルオーバー機構。VRF／VRH を活用したリーダー選出やフォールトトレランス
poh_repair  (3) REPAIR_REQ／REPAIR_ACK Tx の組み立て・送受信・検証（REQ は Python で作り、ACK の検証は Rust コアで）
poh_utils	(1)	共通ユーティリティ（エンコーディング、ハッシュ、エラー型の統一、ロギングヘルパなど）
poh_keygen	(1)	鍵生成・管理ライブラリ（ed25519、BLS、Ristretto など鍵マテリアルの生成／シリアライズ）

なぜ必要か？
poh_cli
→ 日常的なチェーン操作（ノードの起動/停止、ステータス確認、トランザクション送信）を一箇所にまとめ、ドキュメント化／補完付きコマンドとして提供するため。

poh_rpc
→ Python／Rust 両面で同じプロトコルを使えるようにし、ノード間通信や外部アプリとの連携をスムーズに。Swagger/OpenAPI, Protobuf 定義から自動生成すれば仕様と実装の齟齬を防げます。

poh_indexer
→ 調査／デバッグ／ウォレット用に「過去の PoH レコードを高速に検索したい」ケースがあるので、時系列インデックスを持った小規模 DB 層を提供しておくと便利です。

poh_validator
→ フェデレーション運用で複数ノードのリーダー選出や障害切り離しが必要な場合に、VRF／RVH などを組み込んだ再利用可能なモジュールとして切り出します。
→ 受信した PoH_ACK Tx の署名検証とカウント閾値チェック
「PoH 数 >= MIN_POH_REQUIRED」かどうかを判定

poh_repair 
→ REPAIR_REQ／REPAIR_ACK Tx の組み立て・送受信・検証
（REQ は Python で作り、ACK の検証は Rust コアで）

poh_utils
→ 全クレート横断で必要な汎用機能（Base58/Base64, JSON ラッパ, ログフォーマッタ, エラー共通型など）をまとめておくと、重複実装やバージョン不整合を防げます。

poh_keygen
→ テスト用や運用時に必要な鍵ペアの生成・シリアライズ／デシリアライズを一元化し、安全なストレージ形式やパスワード保護機能を提供します。

これらを加えると…

ユーザー向け CLI → poh コマンド一式

ネットワーク API → 安定した RPC 層

統計・検索 → インデクサー＋メトリクス

鍵管理・運用 → キー生成・エラー共通型

…といった「本番運用で欲しくなる」周辺機能が綺麗に揃い、PoH エコシステムとしても抜け漏れのないラインナップになります。ご参考まで！
