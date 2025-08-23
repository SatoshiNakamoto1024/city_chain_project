🧠 設計のカギ：Proof of Hold（PoH）をどう実装するか？
要素	内容
署名	保存者の端末秘密鍵で「TxID + timestamp」を署名
検証者	他ノードは PoH署名 を pubkey で検証、保存済と判定
信頼	“保存済Txは5つ以上のPoHが揃ったもののみ処理”というルールで信頼性を担保
削除	TTL期限後、自動で削除。保持者は「保存済だった」という記録だけ残す（TxIDリスト）

Level 0 → 1     : 基本的なTx送信・PoPチェック  ←（過去）
Level 2 → 3     : DAGストレージとPoPに基づくバッチ処理 ←（現状）
Level 4 → 5     : PoH/保存Txとフラグ付きDAGによる制御開始 ←（次）
Level 6 → 7     : 復元Tx/PoH閾値制御/自律再送 ←（進化段階）
Level 8 → 9     : DAG全体での自己修復 + 分散再構築 + 局所的コンセンサス成立
Level 10        : 完全DAG主導型ブロックチェーン（非同期Tx全自動収束）

✅ 直近で進めるべき優先ステップ（おすすめ）
優先	タスク	目的
★1	TxType を導入し、add_transaction()に tx_type: str を明示	FRESH_TX, POH_ACK, REPAIR_REQ などを使い分けるため
★2	PoH_ACK Tx をgRPCの返答ではなく、DAGのノードとして追加	gossipやRPC依存を減らし、**“保存の証拠もTxとして存在”**させる
★3	REPAIR_REQ / REPAIR_ACK のPoC	TTL切れTxに対してDAGから復元可能なTx依頼を送る処理のPoC作成
★4	resolve_tx_type_priority() のようなTxType優先度ロジック	CHECKPOINTやREPAIR_ACKを先に処理させるなどのDAGソート対応

🔒 復元処理への活用：構造と署名ポイント
Tx種別	署名者	署名対象	用途
FRESH_TX	送信者（本人）	トランザクション本文	DAG内の主ノードとして保持
POH_ACK	保存者ノード	tx_id + holder_id	本当に保持している証明
REPAIR_REQ	問い合わせノード	tx_id + requester_id	「このTxを失いました」の証明
REPAIR_ACK	回答ノード	tx_id + responder_id + recovered_data_hash	「この内容が正しいTxです」の証明

sequenceDiagram
  participant A as Node_A (FRESH_TX 送信)
  participant B as Node_B (保存 PoH_ACK)
  participant C as Node_C (復元要求)
  participant D as Node_D (復元回答)

  A->>DAG: FRESH_TX（署名付き）
  B->>DAG: PoH_ACK（署名付き）
  Note over DAG: FRESH_TXが期限切れで削除

  C->>DAG: REPAIR_REQ（署名付き）
  D->>DAG: REPAIR_ACK（署名 + オリジナルTx）

  DAG->>C: Tx再構築 + 署名検証（送信元Aと回答者Dの両方）


✅ クライアント証明書 vs PoH vs Txフラグ（3者比較）
項目	クライアント証明書,	PoH（保存証明Tx）,	Txフラグ（TxType）
目的	ノードやユーザーの「身元の証明」,	トランザクションが「どこに保存されたかの証明」,	Txの「性質分類と処理戦略の識別」
発行者	あなたのCA（認証局）,	ノード自身（DAGノードとしてPoH Txを追加）,	Tx作成者 or DApps
使用場面	署名検証、通信認証、REPAIR_ACKなどの送信元確認,	FRESH_TXの保存証明、REPAIR_REQの応答根拠,	DAG内でのTx分類（PoH系・受信系・完了系など）
署名との関係	署名生成に必要な公開鍵を保持,	PoHの署名はこの証明書の秘密鍵で生成,	署名そのものではない（Txのメタ情報）
構造	JSON or X.509 PEM証明書（公開鍵含む）,	JSON型の署名付きPoH Tx（DAGノード）,	Enumなどで静的に定義された識別子
不変性	一度発行されたら失効/更新まで変わらない,	PoHはTxごと・ノードごとに動的に生成,	TxTypeはTxごとに固定（変わらない）
例えるなら	「運転免許証」：誰が行為をしたか証明,	「レシート」：そのTxが保存された証拠,	「ラベル」：そのTxが何の目的か識別するための分類タグ


✅ まとめ：本質的な違い
比較軸	クライアント証明書,	PoH,	Txフラグ
証明するもの	「誰が行ったか」,	「どこに保存されたか」,	「何をすべきTxか」
目的	信頼・認証・本人性確認,	分散保存の証明・復元可能性,	処理分岐・分類制御
データ形態	鍵ペア付き証明書（CA署名）,	トランザクション（署名済）,	enumやstringタグ
実際の使われ方	署名付きTxの検証、REPAIR時の復元正当性確認など,	DAGにPoHノードとして追加、保存副本数の判定など,	処理エンジンで処理順序や承認方法を決定する材料


# Proof of Hold (PoH) ― “保存の証拠” を 1 秒未満で確定させるロジック ―
目的
Tx が少なくとも N 副本（例 5 副本）ライトノードに保持された事実を暗号学的に証明
将来その Tx がローカル TTL を超えて失われても、REPAIR _REQ/_ACK で瞬時に復元できる根拠を残す
保存貢献度を 報酬トークン に結びつける

1. データ構造
フィールド	型	説明
tx_id	str	証明対象のオリジナル Tx ID
holder_id	str	保存ノードの NodeID (= 証明書 CN)
timestamp	float	PoH 発行 UNIX 時間（秒）
storage_hash	str	sha256(tx_raw_bytes) ― 本当に保管しているバイト列ハッシュ
sig_alg	str	dilithium3 など
signature	str(base64)	sign(holder_priv, tx_id‖storage_hash‖timestamp)

PoH 自体は Tx として DAG に組み込む：tx_type="poh_ack"
→ 誰でも歴史的に検証できる。

2. 完全なライフサイクル
ステップ	処理内容	典型レイテンシ
① PoH_REQUEST Tx 生成	FRESH Tx 発行ノードが 並列 に 10 近傍ノードへ送る（gRPC or UDP）	～50 ms
② 空き容量チェック	100 MB 予約領域 ≥ 2 KB? → 可なら保持	1–5 ms
③ PoH_ACK Tx 作成	上記データ構造で署名、DAG に追加＆返送	30 ms
④ PoH 集約	オリジナル Tx に “edge” を張り PoH 数をカウント	〈0 ms（DAG挿入時）〉
⑤ 完了判定	PoH_cnt ≥ MIN_POH (5) → Tx 状態＝“store_confirmed”	～0.3 s 総計
⑥ TTL 到来後	PoH_Ack は残り、実データは LRU 消去（容量上限を維持）	6 h など

4. セキュリティ & フォールト耐性
脅威	対策
偽 PoH	署名を CA 発行のクライアント証明書公開鍵で必ず検証
リプレイ攻撃	PoH の timestamp + nonce で 1 分以内のみ有効
容量詐称	storage_hash をランダムサンプリング照会して spot-check
シャード集中	select_candidate_nodes() で PoP + ランダム を併用し負荷分散
大量 PoH Flood	1 Tx に対する PoH を MAX = 16 でカットし DoS 防止

5. PoH と報酬アルゴリズムの結合
def on_poh_ack_confirmed(poh):
    score = calc_geo_weight(poh.holder_id, poh.original_tx_id)  # PoP倍率
    reward_system.record_contribution(poh.holder_id, score)

保存した瞬間ではなく、PoH が “accepted” になった瞬間に報酬を確定
スコアは地理距離・オンライン率・TTL まで保持した実績で増加可能

6. PoH が復元を支える仕組み
REPAIR_REQ Tx には original_tx_id を含む
DAG が PoH_Ack を参照 → 保持ノードを即特定
最も近い保持者が REPAIR_ACK で暗号化済み Tx を再送
署名検証で改ざんゼロ／PoH との一致を確認
→ PoH を“アドレス帳”として使い 1 秒以内に復元完了。

# 実装分担イメージ
処理	Python	Rust
PoH_REQUEST 発行	●python
空き容量チェック・Tx保存	●python
Dilithium 署名生成	（FFI 経由で呼び出し）	●rust
PoH_ACK Tx 組み立て & DAG 追加	●python
PoH_ACK 受信時の署名検証		●rust
PoH 閾値カウント & “保存完了” 判定		●rust
TTL 到来後の GC	●python


#　後の受信者が受信時に復元するが、このとき、誰も保存した人がログインしていない場合は復元不可能となる。それを防ぎたい。よって、gossipは使わないよ！
どんな状況でも、トランザクションを「確実に」「高速で」「安全に」復元する仕組み です。
🔁 普段：ライトノードだけで済む（超高速）
トランザクションは、ライトノード（スマホやIoTなど）に分散してピースとして保存される。

受信者がログインすると、その場でピースを集めて数十ミリ秒で復元できる。

🧯 でも万が一：
ライトノードが全員オフラインだったり、データが壊れていても…

✅ 4段階の「バックアップルート」で、絶対復元できる：
ステップ	役割	時間	例えるなら
① ライトノード復元	本命	50ms	財布からお金を取り出す感覚
② フルノード復元	予備	100ms	銀行のATMで下ろす感じ
③ MongoDB復元	保険	300ms	通帳を持って銀行窓口で聞く感じ
④ 大陸ルーター＋immuDB復元	最終手段	600ms	本店に電話して確認する感じ

🔐 セキュリティも安心
端末証明書 + Dilithium署名で「なりすまし」不可。
MongoDBやimmuDBは暗号化 + アクセス制限あり。
不正アクセスはすぐ検知・遮断。

というような、4階層（フルノードは1％未満に抑えたいのでフルノードに全トランザクションを保存するつもりはない。あくまでヘッドのみ保存し、中身はmongoDBに保存させる。）にして、ライトノード99％以上を成立させる。

#　あと、もうひとつ修正が、フラグ。
Sui以上の構想になっている理由
項目	Sui	あなたの構想
Tx分類	Owned / Shared / System	保存 / PoH / 修復 / CheckPoint など最大6種
修復処理	外部ログで再構築	DAG内でREPAIRとしてTx化
DAGの役割	Tx順序記録	Tx保存・確認・修復まで統合
フルノードの役割	コンセンサス + CheckPoint	チェックポイントのみ（PoHはLノード）
並列性	実行単位で並列化	Tx生成、保存、修復すべて非同期並列化

2. 各Txテンプレート（JSON + Python辞書形式）
2.1 PoH Request Tx（保存要求）
{
  "tx_id": "req123",
  "type": "poh_request",
  "original_tx_id": "tx001",
  "requester": "node_A",
  "timestamp": 1700000000.123,
  "signature": "base64(署名)",
}

poh_request_tx = {
    "tx_id": generate_uuid(),
    "type": TxType.POH_REQUEST.value,
    "original_tx_id": "tx001",
    "requester": "node_A",
    "timestamp": time.time(),
    "signature": sign(PRIVATE_KEY, "tx001|node_A")
}

これで開発手順が完了する。


✔️ このモジュール構成で出来ること
DApps → RecoveryManager.trigger_repair()

PEM で署名付き REPAIR_REQ を DAG に追加

PoH_ACK / REPAIR_ACK 受信

フラグ優先で処理 → PoH 閾値 → Rust 並列収束

Rust 側 collect_valid_ack()

閾値数まで REPAIR_ACK が集まったら Python へ OK を返し“次工程へ”

これで「指示 → 復元完了 → 次工程」という一連をフォルダー分離 & モジュール化できました。
必要に応じてネットワーク I/O を gRPC / WebSocket に差し替えるだけで本番環境へ拡張できます。
