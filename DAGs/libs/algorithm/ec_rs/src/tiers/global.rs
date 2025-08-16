// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\tiers\global.rs
//! Global-DAG
//! • 大規模災害時を想定 – パリティ 50 %
//! • Sum-Product BP 20 回 → 失敗時 RS フォールバック

use once_cell::sync::Lazy;
use crate::{
    design::qcpeg::{QcPegConfig, generate, SparseMatrix},
    encoder::LDPCEncoder,
    decoder::{bp::BPDecoder},
    ErasureCoder, ECError,
};

use reed_solomon_erasure::galois_8::ReedSolomon; // fallback

pub const CFG: QcPegConfig = QcPegConfig {
    data_shards: 2048,
    parity_shards: 2048,
    circulant: 64,
    dv: 3, dc: 6,
};

const SEED: u64 = 0x1F_0B_4D;
static H: Lazy<SparseMatrix> = Lazy::new(|| generate(&CFG, SEED)); // 任意の 64bit 数

//---------------- API ---------------------------------------------

pub fn encode(data: &[u8]) -> Vec<Vec<u8>> {
    LDPCEncoder::new(CFG, SEED).encode(data, CFG.data_shards, CFG.parity_shards)
}

pub fn decode(mut shards: Vec<Option<Vec<u8>>>) -> Result<Vec<u8>, ECError> {
    // -------- 1st: BP decoder ----------
    let bp = BPDecoder::new(H.clone(), CFG.data_shards, 20);
    match bp.decode(shards.clone(), CFG.data_shards, CFG.parity_shards) {
        Ok(d) => return Ok(d),
        Err(_) => {
            // -------- Fallback: Reed-Solomon -----------
            let rs = ReedSolomon::new(CFG.data_shards, CFG.parity_shards)
                .map_err(|e| ECError::Decode(e.to_string()))?;
            // Vec<Option<Box<[u8]>>> 转换
            let mut owned: Vec<Option<Box<[u8]>>> =
                shards.into_iter().map(|o| o.map(|v| v.into_boxed_slice())).collect();
            rs.reconstruct(&mut owned).map_err(|e| ECError::Decode(e.to_string()))?;
            let mut out = Vec::new();
            for slice in owned.into_iter().take(CFG.data_shards) {
                out.extend_from_slice(slice.unwrap().as_ref());
            }
            Ok(out)
        }
    }
}
