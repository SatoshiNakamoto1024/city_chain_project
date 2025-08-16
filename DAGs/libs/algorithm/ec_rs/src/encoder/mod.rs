// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\encoder\mod.rs
//! Systematic QC-LDPC encoder
//!
//! 1. Data 部分をそのままコピー  
//! 2. H の “data-part” と掛け算して parity を得る

use rayon::prelude::*;
use crate::{ErasureCoder, ECError, gf::GF256};
use crate::design::qcpeg::{QcPegConfig, SparseMatrix};

mod sparse_mul;
use sparse_mul::sparse_mul;

//──────────────────────────────────────────────

#[derive(Clone)]
pub struct LDPCEncoder {
    h:   SparseMatrix,   // full H (m×n)
    cfg: QcPegConfig,
}

impl LDPCEncoder {
    /// 既に QC-PEG で生成済み H を受け取る
    pub fn new(h: SparseMatrix, cfg: QcPegConfig) -> Self {
        LDPCEncoder { h, cfg }
    }
}

//──────────────────────────────────────────────
// ErasureCoder
//──────────────────────────────────────────────
impl ErasureCoder for LDPCEncoder {
    fn encode(&self,
              data: &[u8],
              k: usize,
              m: usize)
              -> Result<Vec<Vec<u8>>, ECError>
    {
        if k != self.cfg.data_shards || m != self.cfg.parity_shards {
            return Err(ECError::Config("k/m mismatch with cfg".into()));
        }

        let shard_len = (data.len() + k - 1) / k;
        let total     = k + m;
        let mut shards = vec![vec![0u8; shard_len]; total];

        // 1. copy data shards
        for i in 0..k {
            let start = i * shard_len;
            let end   = ((i + 1) * shard_len).min(data.len());
            shards[i][..end-start].copy_from_slice(&data[start..end]);
        }

        // 2. compute parity shards       (並列＋SIMD)
        let parity = sparse_mul(&self.h, &shards[..k]);
        shards[k..].clone_from_slice(&parity);

        Ok(shards)
    }
}
