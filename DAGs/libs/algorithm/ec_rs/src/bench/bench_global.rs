// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\bench\bench_global.rs
use criterion::{criterion_group, criterion_main, Criterion, Throughput};
use ldpc::tiers::global;
use rand::{Rng, SeedableRng};

fn bench_global_total(c: &mut Criterion) {
    let mut rng = rand::rngs::StdRng::seed_from_u64(99);
    let mut data = vec![0u8; 8 << 20]; // 8 MiB
    rng.fill(&mut data[..]);

    // -------- Encode ----------
    c.benchmark_group("global_encode_8MiB")
        .throughput(Throughput::Bytes(data.len() as u64))
        .bench_function("encode", |b| {
            b.iter(|| {
                let _ = global::encode(&data);
            })
        });

    // -------- Decode ----------
    let shards = global::encode(&data);
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    for i in 0..(global::CFG.parity_shards / 2) {
        opt[global::CFG.data_shards + i] = None; // 50 % parity 欠損
    }

    c.benchmark_group("global_decode_8MiB")
        .throughput(Throughput::Bytes(data.len() as u64))
        .bench_function("decode", |b| {
            b.iter(|| {
                let _ = global::decode(opt.clone()).unwrap();
            })
        });
}

criterion_group!(benches, bench_global_total);
criterion_main!(benches);
