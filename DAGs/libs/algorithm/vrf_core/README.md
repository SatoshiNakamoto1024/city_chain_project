            +---------------------+
            |     vrf_vectors (1) |
            +----------+----------+
                       |
+------------+         v
| vrf_core(2)| <--- vrf_bls(2), vrf_libsodium(2), vrf_threshold(2)
+-----+------+         |
      |                v
      |           vrf_leader (3)
      |                |
      v                v
  vrf_cli (2)     vrf_python (3)  ← Python利用者向け集約
      \                /
       \              /
        +---- vrf_service (3)  ← 外部化（gRPC/HTTP, KMS/HSM連携）

➕ vrf_core (2) — 共通トレイト/型/整合API
役割: すべての VRF 実装の共通土台（エラー型、VrfProof 仕様、VrfProver/VrfVerifier トレイト、シリアライズ）。
API:
pub trait VrfProver {
    type Sk; type Proof; type Output; type Pk;
    fn prove(sk: &Self::Sk, msg: &[u8]) -> Self::Proof;
}
pub trait VrfVerifier {
    type Pk; type Proof; type Output;
    fn verify(pk: &Self::Pk, msg: &[u8], proof: &Self::Proof) -> Option<Self::Output>;
}
メリット: vrf_leader や上位ロジックが実装非依存になる（BLS/NaClの差替えが容易）。
