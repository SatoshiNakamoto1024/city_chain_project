観点	今回：Gossip なし　　(2)
・メンバーシップ伝搬	❶ Auth Service が 「公式ノード表」 を 1 か所に持つ,❷ 各ノードはログイン時に登録、以後は HTTP/Pub‑Sub で pull
・HRW の入力 (候補ノード集合)	“ログイン表” (RDB / Redis / etc.) から毎回 fetch or cache
・失敗検知 (Dead node) & Re‑Join	監視ジョブ (e.g. NATS JetStream, Prometheus) が死活判定 → 公式表を更新

rvh_membership は (2) Rust‑only クレートとして設計します — 理由は次のとおりです。
| 判定基準                 | 内容                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------- |
| **主たる利用先**           | `rvh_core`（HRW 計算）が Rust 側で使う内部サービス                                                       |
| **実装の主体**            | Redis / Etcd などへの非同期 I/O（`tokio`, `redis‑rs`, `etcd-client` など）と、ノード表キャッシュのロジックを Rust で実装 |
| **Python からの直接呼び出し** | 想定しない（Python アプリが必要なら `pyo3` で *別途* ラッパを作る）                                               |
| **PyO3 依存**          | なし – pure Rust                                                                            |
