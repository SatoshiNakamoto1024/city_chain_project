use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::Mutex;

use crate::types::RepairAck;
static ACK_POOL: Mutex<Vec<RepairAck>> = Mutex::new(Vec::new());

#[pyfunction]
pub fn register_repair_ack(json_str: String) {
    let ack: RepairAck = serde_json::from_str(&json_str).unwrap();
    ACK_POOL.lock().unwrap().push(ack);
}

#[pyfunction]
pub fn collect_valid_ack(min_count: usize, target_tx: String) -> Option<Vec<RepairAck>> {
    let mut pool = ACK_POOL.lock().unwrap();
    let res: Vec<_> = pool
        .par_iter()
        .filter(|ack| ack.original_tx_id == target_tx)
        .take(min_count)
        .cloned()
        .collect();
    if res.len() >= min_count {
        // remove consumed
        pool.retain(|ack| ack.original_tx_id != target_tx);
        Some(res)
    } else {
        None
    }
}
