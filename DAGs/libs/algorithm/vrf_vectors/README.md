➕ vrf_vectors (1) — 公式/自前テストベクタ集 & 検証ユーティリティ
役割: JSON/CSVのテストベクタ、クロス実装一致性テスト、ベンチの固定データ。
API:
# Pythonからも読めるテストベクタ（JSON）
# Rust側: crate::vectors::load("bls_draft_vectors.json")
メリット: CIで全実装の相互検証を安定運用できる。Pythonだけでも使えるため (1)。