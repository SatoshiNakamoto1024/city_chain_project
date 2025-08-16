// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\benches\bench_faultset_failover.rs

use criterion::{criterion_group, criterion_main, Criterion};
use rvh_faultset_rust::faultset::failover;

fn bench_failover(c: &mut Criterion) {
    let size     = 1_000;
    let nodes: Vec<String>  = (0..size).map(|i| format!("n{}", i)).collect();
    let lats:  Vec<f64>     = (0..size).map(|i| (i % 200) as f64).collect();

    c.bench_function("failover_1000", |b| {
        b.iter(|| {
            let _ = failover(&nodes, &lats, 100.0).unwrap();
        })
    });
}

criterion_group!(benches, bench_failover);
criterion_main!(benches);
