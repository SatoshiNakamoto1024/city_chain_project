// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\benches\bench_simd_hash.rs
use criterion::{criterion_group, criterion_main, Criterion};
use rvh_simd::score_u128_simd;

pub fn bench_score(c: &mut Criterion) {
    c.bench_function("score_u128_simd", |b| {
        b.iter(|| {
            let _ = score_u128_simd("node-XYZ-999", "object-ABC-1234567890").unwrap();
        })
    });
}

criterion_group!(benches, bench_score);
criterion_main!(benches);

