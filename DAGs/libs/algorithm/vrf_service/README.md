➕ vrf_service (3) — gRPC/HTTP サービス化
役割: VRFをプロセス外で使いたいときの署名サービス（KMS/HSM連携もここ）。
API: POST /vrf/prove, POST /vrf/verify（tonic + Axum など）
メリット: アプリからはネットワーク越しに使える。キー管理とローテーションを集中管理。
