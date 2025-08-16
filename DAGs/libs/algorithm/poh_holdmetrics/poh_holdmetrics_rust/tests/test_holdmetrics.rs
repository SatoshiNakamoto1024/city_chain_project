// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_holdmetrics.rs
//! 核心ロジック (calc_score, HoldAggregator) のユニットテスト
use chrono::{Duration, Utc};
use poh_holdmetrics_rust::{
    calc_score,
    holdset::HoldAggregator,
    model::HoldEvent,
};

#[test]
fn score_empty_is_zero() {
    assert_eq!(calc_score(&[]).unwrap(), 0.0);
}

#[test]
fn score_basic_weight() {
    let now = Utc::now();
    let ev = HoldEvent {
        token_id: "x".into(),
        holder_id: "y".into(),
        start: now - Duration::seconds(10),
        end: Some(now),
        weight: 1.5,
    };
    let sc = calc_score(&[ev]).unwrap();
    assert_eq!(sc, 15.0);
}

#[test]
fn aggregator_accumulates() {
    let agg = HoldAggregator::default();
    let now = Utc::now();
    let ev1 = HoldEvent {
        token_id: "t1".into(),
        holder_id: "alice".into(),
        start: now - Duration::seconds(3),
        end: Some(now),
        weight: 1.0,
    };
    let ev2 = HoldEvent { start: now - Duration::seconds(7), ..ev1.clone() };

    agg.record(&ev1).unwrap();
    agg.record(&ev2).unwrap();

    let snap = agg.snapshot();
    assert_eq!(snap.len(), 1);
    assert_eq!(snap[0].total_seconds, 10);
    assert_eq!(snap[0].weighted_score, 10.0);
}
