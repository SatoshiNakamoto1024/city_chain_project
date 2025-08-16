// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\mod.rs

#[cfg(feature="reed-solomon")]
pub mod reed_solomon;
pub mod erasure_coder;
pub mod ldpc;
pub mod fountain;

pub use reed_solomon::ReedSolomonCoder;

// trait は erasure_coder.rs にのみ置く
pub use erasure_coder::{ErasureCoder, ECError};