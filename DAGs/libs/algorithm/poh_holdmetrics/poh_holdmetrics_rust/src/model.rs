// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\model.rs
//! Shared data structures (Serde + Prost compatible)
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HoldEvent {
    pub token_id: String,
    pub holder_id: String,
    pub start: DateTime<Utc>,
    pub end: Option<DateTime<Utc>>,
    #[serde(default = "default_weight")]
    pub weight: f64,
}
fn default_weight() -> f64 { 1.0 }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HoldStat {
    pub holder_id: String,
    pub total_seconds: i64,
    pub weighted_score: f64,
    pub updated_at: DateTime<Utc>,
}
