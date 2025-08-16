# 「だれもログインしていないライトノードでも 500 ms 以内に必ず復元したい」
── そのための 4 段フェイルオーバー経路 と 指令フロー を 1 枚で理解する

優先度①        優先度②           優先度③              優先度④
オンラインLN ▶ オンラインFN ▶ Mongo Hot ▶ Continent Router + immuDB
     50 ms          100 ms           300 ms                  1 s 超でも可
記号	所要遅延(p95)	主な動き	認証 & 防御
LN
ライトノード	5–50 ms	シャード k/ n & PoH_ACK を返す	端末証明書 + Dilithium
FN
フルノード	30–100 ms	RAM/SSD に持つ「Tx ヘッダ + Mongo キー」から直返し	HSM / TLS mTLS
Mongo Hot	50–300 ms	FN が索引付き find({tx_id})	VPC + IP Allow + IAM
Continent Router	200–400 ms	別リージョン Mongo / immuDB を検索し
RESCUE_BUNDLE を近接 FN へプッシュ	Geo-DNS + Anycast
証明ハッシュ

1. ライトノードが 0 台オンラインだった時の復元シーケンス
sequenceDiagram
  participant Req as Requesting LN
  participant FN  as City-FullNode
  participant DB  as Mongo Hot
  participant CTR as Continent Router
  participant FN2 as Remote FN
  participant IMMU as immuDB

  Req->>FN: REPAIR_REQ(tx_id) ①
  alt ヘッダ命中
      FN->>DB: find(tx_id) ②
      DB-->>FN: {payload, sig}
      FN-->>Req: REPAIR_ACK ③
  else City cluster dead
      Req->>CTR: ESCALATE_REQ ④
      CTR->>IMMU: query(tx_id)
      CTR-->>FN2: RESCUE_BUNDLE
      FN2-->>Req: REPAIR_ACK ⑤
  end
タイムライン目標

フェーズ	目標	備考
① ローカル FN 検出	< 50 ms	“ヘッダ LRU” に tx_id→mongoKey
② Mongo find	50–200 ms	tx_id 索引 + WiredTiger cache
③ 署名再付与 + 送信	< 30 ms	Dilithium 0.3 ms + gzip
合計(通常)	< 300 ms	500 ms 以内に余裕
④–⑤ (リージョン障害)	300–600 ms	immu は Append-only ⇒ 読み込み 150 ms

2. なぜ Mongo Hot を フルノードとは独立 クラスタにするのか
理由	メリット
水平スケール単位が違う	TPS 増→フルノード vCPU を増やすだけ。
データ増→Mongo シャードを追加するだけ。
セキュリティ分離	Mongo は VPC 内、FN から mTLS+IAM でしか書けない。侵害面を限定。
障害ドメイン分割	FN 落ちても Mongo は生きている ⇒ Router から直接読める。

3. Continent Router の役割 = “最後の 1 本を探す検索エンジン”
各 City-FN は 完了バッチの Merkle-root を Router に週次 Push
→ Router は「どの Mongo シャード or immuDB に在るか」インデックスだけ保持（数 KB）

Escalate 受信時
ルート→該当バッチ→該当 Tx の blobPtr を即返す
最寄りの生存 FN へ RESCUE_BUNDLE (Tx + PoH) を P2P Push
元のライトノードは 1 RTT で復元
インデックスは RAM 常駐 ⇒ 10 ms 以内でヒット。

4. ハッキングリスク対策
リスク, 	防御
偽 REPAIR_REQ flood	FN で “PoH 有無 + 認証済み証明書 CN” を確認し RateLimit
DB dump 読み取り, 	Mongo 暗号化 at-rest + VPC PrivateSubnet
Continent Router 攻撃, 	Anycast + eBPF DDoS scrubber + read-only key
署名偽造, 	Dilithium + CA mTLS。impossible w/o key.

5. 実装チェックリスト (City-FN 観点)
ヘッダ LRU
header_cache.put(tx_id, {"mongo_key":ObjectId, "poh_cnt":k})
REPAIR_REQ handler

header = cache.get(tx_id) → hit なら Mongo read

miss → 404 を返し Requesting LN が Escalate

Mongo コレクション設計
unfinished_{yyyymm}, 索引 {tx_id:1}
finished_{yyyymm}, TTL index 180 d

Continent Router API
/rescue?tx_id= → returns {region:"ap-northeast", mongo_uri:"…"}


✅ まとめ
通常：ライトノードがオンライン → k/n シャードで 50 ms〜100 ms 復元
全 LN オフライン：フルノード + MongoHot ルート → 200 ms〜300 ms
City 障害：Continent Router → Remote FN + immuDB → 400 ms〜600 ms
全世界障害：immuDB ログから再構築（速度要求なし、監査用）
これで「誰もログインしていないライトノードでも 500 ms 以内に復元」という目標と、ハッキング耐性の両方を同時に満たせます。

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

