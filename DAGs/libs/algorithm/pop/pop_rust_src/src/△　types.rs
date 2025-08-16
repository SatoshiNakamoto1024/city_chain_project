// D:\city_chain_project\Algorithm\PoP\pop_rust\src\types.rs
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
pub struct PolyItem {
    pub city_id: String,
    pub coords:  Vec<(f64, f64)>,   // (lat, lon)
}
