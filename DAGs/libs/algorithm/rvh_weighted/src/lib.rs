// D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted\src\lib.rs
//! rvh_weighted – **重み付き HRW (Highest-Random-Weight)**  
//!
//! * stake / capacity / RTT を 0-1 スケーリングして合成  
//! * SIMD 128-bit ハッシュは `rvh_simd::score_u128_simd()` を再利用  
//!
//! ```rust
//! use rvh_weighted::{NodeInfo, weighted_select};
//! # let key = "tx42";
//! # let infos = vec![
//! #   NodeInfo::new("n1", 1_000, 8_000, 25.0),
//! #   NodeInfo::new("n2",   600, 4_000, 10.0),
//! # ];
//! let top = weighted_select(&infos, key, 1).unwrap();
//! println!("selected = {:?}", top);
//! ```

//! rvh_weighted – **Weighted HRW (Highest‐Random‐Weight)**
//! * stake / capacity / RTT を 0-1 スケーリングして合成  
//! * SIMD 128-bit ハッシュは `rvh_simd::score128()` を再利用  
#![warn(missing_docs)]

pub mod utils;
pub mod weighted;

/// crate ルートからも NodeInfo／weighted_select を呼べるように再エクスポート
pub use weighted::{NodeInfo, weighted_select};

/// SIMD スコアだけを使いたいとき
pub use utils::score128;

#[cfg(test)]
mod tests {
    // 明示的に weighted モジュールから必要な型／関数をインポート
    use crate::weighted::{NodeInfo, weighted_select};
    use serde_json::json;

    #[test]
    fn basic() {
        let nodes = vec![
            NodeInfo::new("a", 100, 1_000, 2.0),
            NodeInfo::new("b", 50, 2_000, 1.0),
            NodeInfo::new("c", 10, 500,   3.0),
        ];
        let sel = weighted_select(&nodes, "k1", 2).unwrap();
        assert_eq!(sel.len(), 2);
    }

    #[test]
    fn serde_roundtrip() {
        let n = NodeInfo::new("x", 1, 2, 3.0);
        let j = serde_json::to_value(&n).unwrap();
        assert_eq!(j, json!({"id":"x","stake":1,"capacity":2,"rtt_ms":3.0}));
    }
}
