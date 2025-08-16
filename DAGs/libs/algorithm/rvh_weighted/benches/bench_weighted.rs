// D:\city_chain_project\DAGs\libs\algorithm\rvh_weighted\benches\bench_weighted.rs

use criterion::{criterion_group, criterion_main, Criterion};
use rvh_weighted::{NodeInfo, weighted_select};

fn bench_weighted(c: &mut Criterion) {
    // ① 1_000 個のノード ID を String で生成
    let keys: Vec<String> = (0..1_000)
        .map(|i| format!("n{i}"))
        .collect();

    // ② String の参照 (&str) を渡して NodeInfo を構築
    let nodes: Vec<NodeInfo> = keys.iter()
        .enumerate()
        .map(|(i, key)| {
            // stake, capacity を u64 にキャスト
            let stake    = (500u64).saturating_add(i as u64);
            let capacity = (1000u64).saturating_add((i as u64) * 10);
            let rtt_ms   = 5.0 + (i % 30) as f64;
            NodeInfo::new(key.as_str(), stake, capacity, rtt_ms)
        })
        .collect();

    // ベンチ本体
    c.bench_function("weighted_select_k5", |b| {
        b.iter(|| {
            let _ = weighted_select(&nodes, "bench-key", 5).unwrap();
        })
    });
}

criterion_group!(benches, bench_weighted);
criterion_main!(benches);
