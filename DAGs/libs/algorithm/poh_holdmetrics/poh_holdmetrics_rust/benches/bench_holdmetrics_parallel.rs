// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\benches\bench_holdmetrics_parallel.rs
//! 多スレッド環境で `PyAggregator::record()` 相当のロジック
//! (`HoldAggregator::record()`) をひたすら叩くベンチ。
//!
//! * rayon パラレルイテレータで 4 スレッド程度を想定
//! * 20 k × 10 iteration ~= 200 k ops / ベンチ 1 回
//!
//! `cargo bench --bench bench_holdmetrics_parallel` で実行。
use std::{hint::black_box, sync::Arc};

use chrono::{Duration, Utc};
use criterion::{criterion_group, criterion_main, Criterion};
use poh_holdmetrics_rust::{holdset::HoldAggregator, model::HoldEvent};
use rayon::prelude::*;

fn bench_parallel_record(c: &mut Criterion) {
    // ── テストデータ 20 k 件 ───────────────────────────────────
    let now = Utc::now();
    let events: Vec<HoldEvent> = (0..20_000)
        .map(|i| HoldEvent {
            token_id: format!("t{i}"),
            holder_id: format!("user{i:04}"),
            start: now - Duration::seconds(i as i64),
            end:   Some(now),
            weight: 1.0,
        })
        .collect();

    c.bench_function("record() × 20k (rayon)", |b| {
        b.iter(|| {
            // 毎イテレーションごとにまっさらな Aggregator を用意
            let agg = Arc::new(HoldAggregator::default());

            // パラレルに record()
            events.par_iter().for_each(|ev| {
                // clone せず参照渡し → record は &HoldEvent 受け取り
                agg.record(black_box(ev)).unwrap();
            });

            // snapshot() もベンチ対象に含める（重み計算）
            let snap = agg.snapshot();
            black_box(snap);
        })
    });
}

criterion_group!(benches, bench_parallel_record);
criterion_main!(benches);
