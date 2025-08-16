// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\lib.rs
//! Public entry point  ── QC-LDPC 実装
//!
//! * GF(2⁸) 演算        …… `gf.rs`
//! * H 行列生成         …… `design::*`
//! * Systematic Encode …… `encoder::*`
//! * 多方式 Decode      …… `decoder::*`
//!
//! ────────────────────────────────────

mod gf;
pub  use gf::GF256;

pub mod design;
pub mod encoder;
pub mod decoder;

// ─────────────────────────────
// Error & 共通トレイト
// ─────────────────────────────

/// ライブラリ共通エラー
#[derive(Debug, thiserror::Error)]
pub enum ECError {
    #[error("config error: {0}")]
    Config(String),
    #[error("encode error: {0}")]
    Encode(String),
    #[error("decode error: {0}")]
    Decode(String),
    #[error("internal error: {0}")]
    Internal(String),
}

/// “k-of-n” エンコード / デコード共通トレイト
pub trait ErasureCoder: Send + Sync + 'static {
    /// `k+m` 個に分割
    fn encode(&self, data: &[u8], k: usize, m: usize)
        -> Result<Vec<Vec<u8>>, ECError>;

    /// 欠損許容で復元
    fn decode(&self,
              shards: Vec<Option<Vec<u8>>>,
              k: usize,
              m: usize)
        -> Result<Vec<u8>, ECError>
    {
        let _ = (shards, k, m);
        Err(ECError::Decode("decode() not implemented".into()))
    }
}

// 便利 re-export
pub use encoder::LDPCEncoder;
pub use decoder::{
    peeling::PeelingDecoder,
    min_sum::MinSumDecoder,
    bp::BPDecoder,
};

// ─────────────────────────────
// DAG-tier プリセット & API
// ─────────────────────────────
pub mod tiers {
    //! City / Continent / Global 向け QC-LDPC プロファイル

    use once_cell::sync::Lazy;
    use super::{design::qcpeg::{QcPegConfig, generate, SparseMatrix},
                encoder::LDPCEncoder};

    // ── City DAG ─────────────────────
    pub const CITY_CFG: QcPegConfig = QcPegConfig {
        data_shards:   1_024,
        parity_shards:   512,
        circulant:        32,
        dv: 3, dc: 6,
    };
    const CITY_SEED: u64 = 0xC110_C17E;
    static CITY_H: Lazy<SparseMatrix> =
        Lazy::new(|| generate(&CITY_CFG, CITY_SEED));

    pub fn city_encode(data: &[u8])
        -> Result<Vec<Vec<u8>>, super::ECError>
    {
        LDPCEncoder::new(CITY_H.clone(), CITY_CFG)
            .encode(data, CITY_CFG.data_shards, CITY_CFG.parity_shards)
    }

    // ── Continent DAG ────────────────
    pub const CONTINENT_CFG: QcPegConfig = QcPegConfig {
        data_shards:   1_024,
        parity_shards:   768,
        circulant:        32,
        dv: 3, dc: 6,
    };
    const CONT_SEED: u64 = 0xC011_7111;
    static CONT_H: Lazy<SparseMatrix> =
        Lazy::new(|| generate(&CONTINENT_CFG, CONT_SEED));

    pub fn continent_encode(data: &[u8])
        -> Result<Vec<Vec<u8>>, super::ECError>
    {
        LDPCEncoder::new(CONT_H.clone(), CONTINENT_CFG)
            .encode(data, CONTINENT_CFG.data_shards, CONTINENT_CFG.parity_shards)
    }

    // ── Global DAG ───────────────────
    pub const GLOBAL_CFG: QcPegConfig = QcPegConfig {
        data_shards:   2_048,
        parity_shards: 2_048,
        circulant:        64,
        dv: 3, dc: 6,
    };
    const GLOBAL_SEED: u64 = 0x61_0B_4EAF;
    static GLOBAL_H: Lazy<SparseMatrix> =
        Lazy::new(|| generate(&GLOBAL_CFG, GLOBAL_SEED));

    pub fn global_encode(data: &[u8])
        -> Result<Vec<Vec<u8>>, super::ECError>
    {
        LDPCEncoder::new(GLOBAL_H.clone(), GLOBAL_CFG)
            .encode(data, GLOBAL_CFG.data_shards, GLOBAL_CFG.parity_shards)
    }
}
