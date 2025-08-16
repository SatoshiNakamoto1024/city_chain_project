// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\tiers\continent.rs
//! Continent-DAG
//! • 同じ行列サイズ (1024+768) だが余裕を持たせたパリティ
//! • Min-Sum 8 回、早期収束チェック付き

use once_cell::sync::Lazy;
use crate::{
    design::qcpeg::{QcPegConfig, generate, SparseMatrix},
    encoder::LDPCEncoder,
    decoder::min_sum::MinSumDecoder,
    ErasureCoder, ECError,
};

pub const CFG: QcPegConfig = QcPegConfig {
    data_shards: 1024,
    parity_shards: 768,
    circulant: 32,
    dv: 3, dc: 6,
};

const SEED: u64 = 0xC0_11_71;          // 例: 0xC01171
static H: Lazy<SparseMatrix> = Lazy::new(|| generate(&CFG, SEED)); // 例えば 0xC0NT1 → 0xC0NT1_u64 (= hex 0xC0NT1)

//------------- API -----------------------------------------------

pub fn encode(data: &[u8]) -> Vec<Vec<u8>> {
    LDPCEncoder::new(CFG, SEED).encode(data, CFG.data_shards, CFG.parity_shards)
}

pub fn decode(shards: Vec<Option<Vec<u8>>>) -> Result<Vec<u8>, ECError> {
    let dec = MinSumDecoder::new(
        H.clone(),
        CFG.data_shards,
        CFG.parity_shards,
        8,        // max_iter
        0.85,     // scale
    );
    dec.decode(shards, CFG.data_shards, CFG.parity_shards)
}
