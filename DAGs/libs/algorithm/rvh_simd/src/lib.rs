// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\src\lib.rs
//! rvh_simd ― SIMD‐accelerated hash score
#![warn(missing_docs)]

pub mod simd_hash;

// 元の関数名も再エクスポートしつつ、alias も残す
pub use simd_hash::{
    score_u128_simd,               // ← これを追加
    score_u128_simd as score128,
    HashScoreError,
};
