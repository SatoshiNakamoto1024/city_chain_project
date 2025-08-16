// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\bench\bench_city.rs
use criterion::{criterion_group, criterion_main, Criterion, Throughput};
use ldpc::tiers::city;
use rand::{Rng, SeedableRng};

fn bench_city_encode(c: &mut Criterion) {
    let mut rng = rand::rngs::StdRng::seed_from_u64(42);
    let mut data = vec![0u8; 4 << 20];      // 4 MiB
    rng.fill(&mut data[..]);

    c.benchmark_group("city_encode_4MiB")
        .throughput(Throughput::Bytes(data.len() as u64))
        .bench_function("encode", |b| {
            b.iter(|| {
                let _ = city::encode(&data);
            })
        });
}

fn bench_city_decode(c: &mut Criterion) {
    let mut rng = rand::rngs::StdRng::seed_from_u64(7);
    let mut data = vec![0u8; 4 << 20];
    rng.fill(&mut data[..]);

    let shards = city::encode(&data);
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    for i in 0..opt.len() { if i % 9 == 0 { opt[i] = None; } }

    c.benchmark_group("city_decode_4MiB")
        .throughput(Throughput::Bytes(data.len() as u64))
        .bench_function("decode", |b| {
            b.iter(|| {
                let _ = city::decode(opt.clone()).unwrap();
            })
        });
}

criterion_group!(benches, bench_city_encode, bench_city_decode);
criterion_main!(benches);
