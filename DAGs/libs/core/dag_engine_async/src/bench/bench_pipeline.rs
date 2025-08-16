// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\bench\bench_pipeline.rs
//! Criterion ベンチ:  5 MiB を QC-LDPC エンコード → MPSC → dummy sink
use criterion::{criterion_group, criterion_main, Criterion};
use tokio::{runtime::Runtime, sync::mpsc};
use ldpc::{
    encoder::LDPCEncoder,
    pipeline::{encode_stream, Tier},
    tiers::{CITY_CFG},
};

fn bench_encode(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    c.bench_function("stream_encode_city", |b| {
        b.to_async(&rt).iter(|| async {
            let data = vec![0u8; 5 * 1024 * 1024];

            let (mut r, mut w) = tokio::io::duplex(64 * 1024);
            tokio::spawn(async move { w.write_all(&data).await.unwrap() });

            let enc = LDPCEncoder::new(CITY_CFG, 0xC17E);
            let (tx, mut rx) = mpsc::channel(128);
            encode_stream(&mut r, enc, Tier::City, tx);

            // drain packets without network I/O
            while let Some(_) = rx.recv().await {}
        });
    });
}

criterion_group!(benches, bench_encode);
criterion_main!(benches);
