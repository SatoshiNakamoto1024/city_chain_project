// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\benches\benvh_hwr_score.rs

use criterion::{criterion_group, criterion_main, Criterion};
use rvh_rust::utils::score_u128;

/// score_u128 をベンチマークする Criterion ベンチ関数
fn bench_score(c: &mut Criterion) {
    c.bench_function("score_u128", |b| {
        b.iter(|| {
            // 擬似ノードとオブジェクトのペアでハッシュスコアを計算
            let _ = score_u128("node-XYZ-999", "object-ABC-1234567890");
        })
    });
}

criterion_group!(benches, bench_score);
criterion_main!(benches);
