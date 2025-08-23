// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\src\lib.rs
//! LDPC Erasure Coding module
//!
//! Provides `LDPCEncoder` and `LDPCDecoder` implementing `ErasureCoder` for
//! k-of-n recovery via LDPC codes over GF(2^8).

mod matrix;
mod encoder;
mod decoder;

pub use encoder::LDPCEncoder;
pub use decoder::LDPCDecoder;

/// Erasure coding plugin trait
pub trait ErasureCoder {
    /// Encode `data` into `k + m` shards (first k are data shards, next m are parity shards)
    fn encode(
        &self,
        data: &[u8],
        k: usize,
        m: usize,
    ) -> Result<Vec<Vec<u8>>, ECError>;

    /// Decode original data from up to k present shards.
    /// `shards.len() == k + m`, missing entries as `None`.
    fn decode(
        &self,
        shards: Vec<Option<Vec<u8>>>,
        k: usize,
        m: usize,
    ) -> Result<Vec<u8>, ECError>;
}

/// Error type for LDPC operations
#[derive(Debug, thiserror::Error)]
pub enum ECError {
    #[error("Configuration error: {0}")]
    Config(String),
    #[error("Encoding error: {0}")]
    Encode(String),
    #[error("Decoding error: {0}")]
    Decode(String),
    #[error("Linear solve error: {0}")]
    Solve(String),
}
