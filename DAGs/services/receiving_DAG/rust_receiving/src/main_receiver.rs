//! cargo run --example main_recovery
use receiving_DAG::recovery::{register_repair_ack, collect_valid_ack};

fn main() {
    let json = r#"{
        "tx_id":"ack123","original_tx_id":"tx123",
        "responder":"NodeX","timestamp":0.0,
        "recovered_tx":{},"signature":"abc"
    }"#;
    register_repair_ack(json.into());
    let ok = collect_valid_ack(1, "tx123".into());
    println!("collect = {}", ok.is_some());
}
