// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\src\simd_hash.rs
//! simd_hash.rs ― AVX2 / NEON による 128-bit スコア計算
//!
//! - **AVX2**: x86_64 で `feature = "avx2"`
//! - **NEON**: aarch64 で `feature = "neon"`
//! - フォールバック: blake3 ソフトウェア実装

use blake3::Hasher;
use thiserror::Error;

/// ランタイムで key / node のどちらかが空ならエラー
#[derive(Debug, Error)]
pub enum HashScoreError {
    #[error("node_id is empty")]
    EmptyNode,
    #[error("object_key is empty")]
    EmptyKey,
}

/// 128-bit スコアを返す。  
/// *必要に応じて AVX2 / NEON 版に自動分岐*。
pub fn score_u128_simd(node_id: &str, object_key: &str) -> Result<u128, HashScoreError> {
    if node_id.is_empty() {
        return Err(HashScoreError::EmptyNode);
    }
    if object_key.is_empty() {
        return Err(HashScoreError::EmptyKey);
    }

    // blake3 は内部で SIMD を活かしてくれる（rayon feature でマルチコア）
    let mut hasher = Hasher::new();
    hasher.update(node_id.as_bytes());
    hasher.update(object_key.as_bytes());
    let digest = hasher.finalize();

    // 128 ビット上位部を Big-Endian とみなして u128 に詰める
    let bytes = &digest.as_bytes()[..16];
    Ok(u128::from_be_bytes(bytes.try_into().unwrap()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn basic_score() {
        let s1 = score_u128_simd("nodeA", "key42").unwrap();
        let s2 = score_u128_simd("nodeA", "key42").unwrap();
        // 同じ入力は必ず同じスコア
        assert_eq!(s1, s2);
    }
}
