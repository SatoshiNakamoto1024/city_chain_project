use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone)]
pub struct RepairAck {
    pub tx_id: String,
    pub original_tx_id: String,
    pub responder: String,
    pub timestamp: f64,
    pub recovered_tx: serde_json::Value,
    pub signature: String,
}
