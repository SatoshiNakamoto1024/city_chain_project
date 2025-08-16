// sending_DAG\rust_sending\flag_sort\src\types.rs
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
pub struct FlagTuple {
    pub flag: String,
    pub json: serde_json::Value,
}
