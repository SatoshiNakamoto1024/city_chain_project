// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\benches\bench_holdmetrics_calc.rs
//! 単純に `calc_score()` だけをベンチする。
//! `cargo bench --bench bench_holdmetrics_calc` で実行。

use std::hint::black_box;

use chrono::{Duration, Utc};
use criterion::{criterion_group, criterion_main, Criterion};
use poh_holdmetrics_rust::{calc_score, model::HoldEvent};

fn bench_calc(c: &mut Criterion) {
    // ── 20 k 件のダミーイベントを生成 ────────────────────────────
    let now = Utc::now();
    let events: Vec<HoldEvent> = (0..20_000)
        .map(|i| HoldEvent {
            token_id: format!("t{i}"),
            holder_id: "user".into(),
            start: now - Duration::seconds(i),
            end:   Some(now),
            weight: 1.0,
        })
        .collect();

    // ── Criterion 計測 ────────────────────────────────────────
    c.bench_function("calc_score 20k events", |b| {
        b.iter(|| {
            // black_box で最適化を抑止
            let score = calc_score(black_box(&events)).unwrap();
            black_box(score);
        })
    });
}

criterion_group!(benches, bench_calc);
criterion_main!(benches);
