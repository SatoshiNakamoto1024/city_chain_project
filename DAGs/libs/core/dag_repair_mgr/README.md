dag_repair_mgr (3)	RepairReq/Ack 管理

│   │   └── recovery/                      ← 復元失敗時の高度リカバリロジック
│   │       ├── mod.rs                     # recovery サブモジュール登録
│   │       ├── strategy.rs                # 欠損状況に応じた再送要求／フェイルオーバー戦略
│   │       └── tracker.rs                 # どのシャードが欠損したか状態管理・リトライ回数制御
│   │

