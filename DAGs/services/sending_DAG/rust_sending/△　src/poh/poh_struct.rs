use serde::{Serialize, Deserialize};
#[derive(Serialize,Deserialize,Clone)]
pub struct PoHTx {
    pub tx_id: String,
    pub holder_id: String,
    pub timestamp: f64,
    pub storage_hash: String,
    pub signature: Vec<u8>,
}
