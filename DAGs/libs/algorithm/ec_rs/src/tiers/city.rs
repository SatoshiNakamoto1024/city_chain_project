// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\tiers\city.rs
//! City-DAG プリセット
//! • dv=3, dc=6, circulant 32
//! • Peeling decoder / 8 MB Shard ≈ 150 MiB/s

use once_cell::sync::Lazy;
use crate::{
    design::qcpeg::{QcPegConfig, generate, SparseMatrix},
    encoder::LDPCEncoder,
    decoder::peeling::PeelingDecoder,
    ErasureCoder, ECError,
};

pub const CFG: QcPegConfig = QcPegConfig {
    data_shards: 1024,
    parity_shards: 512,
    circulant: 32,
    dv: 3, dc: 6,
};

const SEED: u64 = 0xC1_70_FF;          // 好きな数で OK
static H: Lazy<SparseMatrix> = Lazy::new(|| generate(&CFG, SEED)); // 固定シード (hex OK)

//------------- Public API -----------------------------------------

pub fn encode(data: &[u8]) -> Vec<Vec<u8>> {
    LDPCEncoder::new(CFG, SEED).encode(data, CFG.data_shards, CFG.parity_shards)
}

pub fn decode(shards: Vec<Option<Vec<u8>>>) -> Result<Vec<u8>, ECError> {
    let dec = PeelingDecoder::new(H.clone(), CFG.data_shards, CFG.parity_shards);
    dec.decode(shards, CFG.data_shards, CFG.parity_shards)
}
