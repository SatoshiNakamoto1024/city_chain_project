vrf_libsodium (2) – libsodium VRF
✅ vrf_libsodium (2) — libsodium VRF（ed25519‑VRF）
目的: 既存インフラに馴染みやすい libsodium の VRF を Rust から呼ぶ。
主API（Rust）:
pub struct SodiumVrfSecretKey([u8; 64]);
pub struct SodiumVrfPublicKey([u8; 32]);

pub struct VrfProof { pub pi: Vec<u8>, pub y: [u8; 32] }

pub fn keygen() -> (SodiumVrfPublicKey, SodiumVrfSecretKey);
pub fn prove(sk: &SodiumVrfSecretKey, msg: &[u8]) -> VrfProof;
pub fn verify(pk: &SodiumVrfPublicKey, msg: &[u8], proof: &VrfProof) -> bool;
依存例: libsodium-sys（動的/静的リンク切替用の feature）、thiserror
注意: 配布環境ごとの libsodium の在り方（動的/静的）を features = ["vendored"] 等で吸収。
