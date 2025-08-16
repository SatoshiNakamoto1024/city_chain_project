    │
    └── aggregator/          ← 閾値カウント・バッチ集約
        ├── mod.rs
        └── count.rs         ← lock-free 集約テーブル + 完了判定