// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\benches\bench_faultset_parallel.rs

use criterion::{criterion_group, criterion_main, Criterion};
use rayon::prelude::*;

fn bench_parallel(c: &mut Criterion) {
    let size     = 1_000;
    let nodes: Vec<String>  = (0..size).map(|i| format!("n{}", i)).collect();
    let lats:  Vec<f64>     = (0..size).map(|i| (i % 200) as f64).collect();

    c.bench_function("failover_parallel_1000", |b| {
        b.iter(|| {
            // Simple parallel filter
            let _res: Vec<String> = nodes
                .par_iter()
                .zip(lats.par_iter())
                .filter_map(|(n, &lat)| if lat <= 100.0 { Some(n.clone()) } else { None })
                .collect();
        })
    });
}

criterion_group!(benches, bench_parallel);
criterion_main!(benches);
