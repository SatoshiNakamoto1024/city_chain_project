vrf_bls (2) – BLS-VRF
目的: BLS12‑381（blst/arkworks 系）で VRF（proof of random output）を提供。集約/しきい値VRFの土台にも。
主API（Rust）:
pub struct BlsVrfSecretKey(...);
pub struct BlsVrfPublicKey(...);
pub struct VrfProof { pub pi: Vec<u8>, pub y: [u8; 32] } // y: VRF出力(ハッシュ)

pub fn keygen<R: rand_core::RngCore>(rng: &mut R) -> (BlsVrfPublicKey, BlsVrfSecretKey);

pub fn prove(sk: &BlsVrfSecretKey, msg: &[u8]) -> VrfProof;

pub fn verify(pk: &BlsVrfPublicKey, msg: &[u8], proof: &VrfProof) -> bool;

// 順序づけ/スコア化向けヘルパ
pub fn output_score(y: &[u8;32]) -> u128;   // HRW/順位付けに使いやすいスコア化
依存例: blst または ark-bls12-381, sha2/blake3, rand_core
特徴: no_std オプション、SerDe可、feature = "fast-verify" でバッチ検証。