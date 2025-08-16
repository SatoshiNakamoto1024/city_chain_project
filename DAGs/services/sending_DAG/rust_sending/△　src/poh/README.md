├── poh/                 ← PoH ロジック・データ構造
    │   ├── mod.rs
    │   ├── poh_struct.rs    ← PoH_Tx struct 定義
    │   ├── signer.rs        ← PoH_ACK 生成 (sign)
    │   └── verifier.rs      ← PoH_ACK 検証 (verify)

PoH（Proof-of-Hold）処理
「tx_id＋storage_hash＋timestamp」への Dilithium 署名生成・検証。
閾値カウントを並列かつロックフリーに行うアグリゲータ。

# 結論
Rust 側（rust_sending/）
→ PoH, NTRU, Dilithium, PoH_ACK 集約 に絞る


✅ PoHの目的と機能（あなたのモデルに即して）
役割	詳細
① 保存の存在証明	PoHは「どのノードがTxを保持しているか」を明示するための署名付きTx。保持ノードの信頼を可視化できる
② DAG内の“承認要件”	あるTxが有効と見なされるためには、一定数（例：5以上）のPoHがDAG内に追加されている必要がある
③ 重複・冗長保存の分散設計	PoHにより「何ノードに保存されているか」が明確になるため、保存の冗長率（分散性）を制御できる
④ 復元時の根拠	TxがTTLで失われても、PoHを保有するノードが REPAIR_ACK にて再配布する正当性を証明できる
⑤ 評価/報酬の証拠	PoHがある＝ノードが保存貢献をした証拠 → record_contribution() によって報酬が与えられる根拠になる
⑥ 完了判定のトリガー	PoHの数 + 受信Txの完了 → これを満たすことで「完了Tx」としてMongoDBに書き込まれる

✅ PoHがあることで可能になる処理の流れ（例）
graph TD
  A[FRESH_TX: tx_abc123] --> B1[PoH_ACK: NodeB]
  A --> B2[PoH_ACK: NodeC]
  A --> B3[PoH_ACK: NodeD]
  B1 --> C[受信者からの完了通知]
  C --> D[mark_transaction_completed()]
  D --> E[MongoDB保存 → push to Continent]

✅ PoHとTxフラグ（TxType）の定義と本質的な違い
項目,	PoH（Proof of Hold）,	Txフラグ（TxType）
目的,	保存者が「このTxを保持している」ことを証明する, 	トランザクションの“性質”や“処理戦略”を分類する
機能,	分散保存の実態を担保し、信頼性・復元性を確保, 	各Txを分類し、DAG内での扱いや優先度、依存関係、承認方法を決定
発行者, 	保存ノード自身（署名付き）, 	Tx作成者 or システム側が付与
DAGへの影響, 	PoHがノードとしてDAGに追加され、辺を作る（保存証明として）, 	DAG構造の中でTxの扱いを切り替えるためのフラグ情報として参照される
動的 or 静的,	動的：PoHはTxごとに複数生成される（副本）, 	静的：Tx作成時に1つだけ設定される属性
主な利用シーン, 	保存の証明、PoH成立判定（≒保存副本数チェック）、復元時の証拠、報酬付与, 	FRESH_TX, POH_ACK, REPAIR_REQ, CHECKPOINT などの役割ごとの処理分岐や優先度制御
例えるなら, 	レシートの束（保存していることの証明書）, 	ラベル（タグ）（このトランザクションは何か）

✅ 両者の関係性を図で表す
FRESH_TX（フラグ: fresh_tx）
 ├─→ PoH_ACK（Node A） ←保存証明Tx（PoH）
 ├─→ PoH_ACK（Node B） ←保存証明Tx（PoH）
 └─→ PoH_ACK（Node C） ←保存証明Tx（PoH）

→ PoH数が一定数超えたら「保存成立」として、次段階へ進行（受信Tx → 完了Tx）
FRESH_TX の Txフラグは "このTxが何者か" を決定する

PoH は "このTxがどこに保存されているか" をDAG上で可視化する

✅ 両者の統合的理解：PoHとTxフラグは共存する
組み合わせ, 	目的
FRESH_TX + PoH_ACK, 	送信者が作成し、保存ノードがPoH証明Txを作る
REPAIR_REQ + PoH_ACK, 	DAGが復元要求Txを作成 → PoH保持ノードが再送応答Txを出す
CHECKPOINT, 	完了TxがPoH/DPoSを経たあと、集約されたバッチを不変化する
POH_ACK というTxType, 	PoHが単なるデータではなく、独立したTxでありTxTypeを持つことを意味する（あなたのモデルならでは）

✅ まとめ
Txフラグ（TxType）は “このトランザクションが何者でどう処理すべきか” を決めるラベルであり、
PoHは “そのTxが本当に保持されているか” を証明する署名付き証拠である。

両者はまったく異なる視点ですが、あなたのDAG構造では両方が完全に組み合わさることで、“保存性＋信頼性＋処理戦略”の三位一体のTx管理が成立します。