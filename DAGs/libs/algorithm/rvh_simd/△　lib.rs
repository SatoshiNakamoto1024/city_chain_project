// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\src\lib.rs
//! rvh_simd ― SIMD‐accelerated hash score
#![warn(missing_docs)]

pub mod simd_hash;

pub use simd_hash::{score_u128_simd as score128, HashScoreError};