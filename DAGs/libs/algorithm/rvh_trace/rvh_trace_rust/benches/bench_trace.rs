// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\benches\bench_trace.rs
//! Criterion + Tokio async benchmark for span creation.

use criterion::{criterion_group, criterion_main, Criterion};
use rvh_trace_rust::{init_tracing, new_span};
use tokio::runtime::Runtime;

/// ベンチ本体
fn bench_trace(c: &mut Criterion) {
    // ── ① 先に Tokio ランタイムを作成 ─────────────────────────────
    let rt = Runtime::new().expect("tokio runtime");

    // ── ② ランタイム内で tracing/OTLP を初期化 ──────────────────
    rt.block_on(async {
        // OnceCell により 1 回しか初期化されません
        init_tracing("warn").expect("tracing init inside runtime");
    });

    // ── ③ 非同期ベンチを実行 ────────────────────────────────────
    c.bench_function("new_span_async", |b| {
        // `to_async` は `criterion` の `async_tokio` フィーチャで有効化済み
        b.to_async(&rt).iter(|| async {
            let span = new_span("bench");
            drop(span);
        })
    });
}

criterion_group!(benches, bench_trace);
criterion_main!(benches);
