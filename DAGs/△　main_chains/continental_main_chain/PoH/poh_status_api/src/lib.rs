// -----------------------------------------------------------------------
// ファイル名: lib.rs
// -----------------------------------------------------------------------
use rocket::{get, serde::json::Json, State};
use rocket::serde::json::Value;
use std::sync::Arc;
use tokio::sync::Mutex;
use chrono::Utc;

// crate 内で定義されている AppState, ProofOfHistory, PoHEvent を use する想定
use crate::{AppState, PoHEvent};

/// PoHの状態 (最新ハッシュ・イベント数・各イベントの詳細) を返すAPI.
///
/// - `latest_hash`: 直近のPoHハッシュ
/// - `count`: PoHに記録されているイベント数
/// - `events`: イベントのリスト（イベント文字列、記録日時、イベントハッシュ）
#[get("/poh_status")]
pub async fn get_poh_status(state: &State<Arc<Mutex<AppState>>>) -> Json<Value> {
    // AppStateのロックを取得
    let state_guard = state.lock().await;
    // AppStateのPoHロックを取得
    let poh_guard = state_guard.poh.lock().await;

    // イベント一覧を取得
    let events_detail = poh_guard.get_events_detail();  // 例: Vec<PoHEvent>
    // 最新ハッシュの取得
    let latest = poh_guard.get_latest_hash().to_string();
    // イベント数
    let count = poh_guard.len();

    // イベントをJSON配列に変換
    // (event_str, recorded_at, event_hash)をまとめて返す
    let events_json: Vec<Value> = events_detail.iter().map(|ev| {
        serde_json::json!({
            "event_str": ev.event_str,
            "recorded_at": ev.recorded_at.to_rfc3339(),
            "event_hash": ev.event_hash
        })
    }).collect();

    // JSON形式で返す
    Json(serde_json::json!({
        "latest_hash": latest,
        "count": count,
        "events": events_json,
    }))
}
