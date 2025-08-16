// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\benches\bench_faultset.rs

//! RVH Faultset のシリアル・並列・非同期版ベンチマーク
use std::time::Duration;
use criterion::{
    criterion_group,
    criterion_main,
    Criterion,
    BenchmarkId,
    Throughput,
};
use rayon::prelude::*;
use tokio::runtime::Runtime;
use rvh_faultset_rust::faultset::{failover, failover_async};

fn bench_failover(c: &mut Criterion) {
    // ベンチマーク・グループ名を "failover_all" に
    let mut group = c.benchmark_group("failover_all");
    group
        .warm_up_time(Duration::from_secs(2))
        .measurement_time(Duration::from_secs(5))
        .sample_size(50);

    // Tokio ランタイムを一度だけ構築
    let rt = Runtime::new().expect("Tokio runtime");

    for &size in &[1_000usize, 10_000, 100_000] {
        // テストデータ生成
        let nodes: Vec<String> = (0..size).map(|i| format!("node{}", i)).collect();
        let lats: Vec<f64> = (0..size).map(|i| (i % 200) as f64).collect();

        // スループット指標として要素数を設定
        group.throughput(Throughput::Elements(size as u64));

        // ----- シリアル版 -----
        group.bench_with_input(
            BenchmarkId::new("serial", size),
            &size,
            |b, &_s| {
                b.iter(|| {
                    let _ = failover(&nodes, &lats, 100.0).unwrap();
                });
            },
        );

        // ----- Rayon 並列版 -----
        group.bench_with_input(
            BenchmarkId::new("parallel", size),
            &size,
            |b, &_s| {
                b.iter(|| {
                    let _res: Vec<String> = nodes
                        .par_iter()
                        .zip(lats.par_iter())
                        .filter_map(|(n, &lat)| if lat <= 100.0 { Some(n.clone()) } else { None })
                        .collect();
                });
            },
        );

        // ----- Tokio 非同期版 -----
        group.bench_with_input(
            BenchmarkId::new("async", size),
            &size,
            |b, &_s| {
                b.iter(|| {
                    // Owned の Vec を clone して async 関数に渡す
                    let fut = failover_async(nodes.clone(), lats.clone(), 100.0);
                    // 同期的に await する
                    let _ = rt.block_on(fut).unwrap();
                });
            },
        );
    }

    group.finish();
}

criterion_group!(benches, bench_failover);
criterion_main!(benches);
