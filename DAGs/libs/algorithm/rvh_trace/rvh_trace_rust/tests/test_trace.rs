// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\tests\test_trace.rs

//! 単体 (Rust だけ) テスト。
//! init_tracing() 内部で tonic が Tokio へアクセスするため、
//! テスト関数を `#[tokio::test]` でラップしてランタイムを用意する。

use rvh_trace_rust::{init_tracing, in_span};
use tokio; // マクロ用。features = ["macros"] が Cargo.toml に既にあるので OK

#[tokio::test(flavor = "current_thread")]
async fn test_trace_sync() {
    // ログレベルは何でも良いが出力が少ない "debug" 程度に
    init_tracing("debug").expect("tracing init");

    // in_span は同期 API なのでそのまま呼ぶ
    let result = in_span("unit_test", &[("user", &123u32)], || {
        tracing::info!("inside sync span");
        42
    });
    assert_eq!(result, 42);
}
