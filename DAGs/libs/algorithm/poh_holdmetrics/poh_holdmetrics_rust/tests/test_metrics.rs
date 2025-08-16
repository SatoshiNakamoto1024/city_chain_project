// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_metrics.rs
//! Prometheus gather テスト：メトリクスが 1 つ以上登録済みか
use poh_holdmetrics_rust::metrics;

#[test]
fn prometheus_metrics_exist() {
    // アクセスすると counters が初期化されて gather に出てくる
    metrics::HOLD_EVENTS.inc();
    let gathered = prometheus::gather();
    let names: Vec<_> = gathered.iter().map(|m| m.get_name()).collect();
    assert!(names.contains(&"hold_events_total"));
}
