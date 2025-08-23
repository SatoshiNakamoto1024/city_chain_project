🔒 より強固な MongoDB 防御策セット（推奨）
項目	内容	補足
✅ VPC 内限定公開	MongoDB はインターネット非公開、PrivateSubnet に置く	踏み台サーバからしかアクセスできないようにする
✅ TLS 通信のみ許可  	MongoDB への接続は TLS 必須＋証明書要件付き,	クライアント証明書（X.509）も活用可
✅ IAM or IP制限	   アプリの実行先 IP からのみ接続可能に, 	SecurityGroup や FW で指定
✅ at-rest 暗号化 (AES256)	Mongoの設定でディスク暗号化を有効化,	OSレベル暗号化 (LUKS, EBS encryption) と併用も可
✅ アクセス監査ログ	誰がいつどのコレクションにアクセスしたかを記録, 	auditLog.destination: file などを設定
✅ rootパスワード分離	アプリに使わせるアカウントは読み書き限定に, 	管理者用 root は完全に分離し、監視対象に

🔐 NTRU と MongoDB は直接関係ある？
MongoDB の at-rest 暗号化は通常 AES256（共通鍵暗号）であり、NTRU ではありません。

ただし：
将来的に NTRU（格子暗号）ベースの 鍵カプセル化（KEM） で「MongoDB の暗号鍵自体を格納する」
という設計は可能です（→ポスト量子セキュリティ）。

✅ まとめ：MongoDB 攻撃対策は
問題	対応
誰でも接続できてしまう	PrivateSubnet + IP制限 + TLS 必須
データ盗難（ディスク・バックアップ）	暗号化 at rest (AES256)
接続後の読み取り（内部犯）	アクセス制限・監査ログ・権限分離
将来の量子攻撃	NTRU/KEM を暗号鍵管理に採用する可能性あり（今はAESで十分）
