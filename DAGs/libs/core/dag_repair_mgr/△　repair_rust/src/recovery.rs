use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::Mutex;
use crate::types::RepairAck;

static POOL: Mutex<Vec<RepairAck>> = Mutex::new(Vec::new());

#[pyfunction]
pub fn register_repair_ack(json_str: String) {
    let ack: RepairAck = serde_json::from_str(&json_str).unwrap();
    POOL.lock().unwrap().push(ack);
}

#[pyfunction]
pub fn collect_valid_ack(min_cnt: usize, target_tx: String)
        -> Option<Vec<RepairAck>> {
    let mut pool = POOL.lock().unwrap();
    let found: Vec<_> = pool.par_iter()
        .filter(|a| a.original_tx_id == target_tx)
        .take(min_cnt)
        .cloned()
        .collect();
    if found.len() >= min_cnt {
        pool.retain(|a| a.original_tx_id != target_tx);
        Some(found)
    } else {
        None
    }
}
