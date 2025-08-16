// D:\city_chain_project\Algorithm\PoP\pop_rust_src\src\types.rs
use serde::{Deserialize, Serialize};

/// Python／Rust 共通で使うポリゴン情報
#[derive(Serialize, Deserialize, Clone)]
pub struct PolyItem {
    /// 市町村名など
    pub city_id: String,
    /// (緯度, 経度) のリスト
    pub coords: Vec<(f64, f64)>,
}
