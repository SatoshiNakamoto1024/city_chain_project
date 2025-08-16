◆ なぜ「フラグ」が重要なのか？
Suiでは「フラグ（Tag）」がトランザクションの処理戦略を決定します：

フラグ	処理方式	対応例
OwnedTx	並列で即実行	NFT mint, アバター作成
SharedTx	コンセンサス必要	トークン移転, 交換
SystemTx	権限付きで遅延実行	ステーキング, ガバナンス

◆ あなたの構想における独自フラグ案（復元含む）
フラグ名	意味	処理方法	特記事項
FRESH_TX	新規Tx	PoHチェック → DAG挿入	通常Tx
POH_REQ	保存依頼	各ノードへPoH依頼送信	TTL付きで自動無視も可
POH_ACK	PoH署名返却	DAGに保存、依存記録	各Txに最低5個必要
CHECKPOINT	チェックポイントTx	フルノードが集約	immuDB書き込み対象
REPAIR_REQ	Tx未達通知	他ノードに復元依頼	TTL 3秒で終了
REPAIR_ACK	Tx復元データ	元Tx内容を再送	AES暗号化 + hash検証

→ このような 「復元専用Txタイプ」 をDAG上に明示しておくことで、復元も並列・非同期で処理できる！

◆ フラグ付きDAG構造（例）
graph TD
  T1[FRESH_TX: Tx001]
  P1[POH_ACK: nodeA]
  P2[POH_ACK: nodeB]
  C1[CHECKPOINT]
  R1[REPAIR_REQ: Tx001]
  R2[REPAIR_ACK: Tx001]

  T1 --> P1
  T1 --> P2
  P1 --> C1
  P2 --> C1
  C1 --> R1
  R1 --> R2
→ このDAG構造だけ見れば「どのTxが何のPoHに支えられていたか、誰が修復したか」まで全部わかる。復元処理がDAGに含まれる！