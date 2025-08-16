// rvh_faultset_rust/src/tests/test_cli.rs

use assert_cmd::Command;
use predicates::prelude::*;

/// CLI が正しくフェイルオーバー結果を返すかテスト
#[test]
fn cli_select_works() {
    // Cargo.toml の [[bin]] name = "main_faultset" に対応
    let mut cmd = Command::cargo_bin("main_faultset").unwrap();

    // ノード a,b,c それぞれのレイテンシ 10,20,30、閾値 20.0 → a,b が残る
    cmd.arg("--nodes")
        .arg("a,b,c")
        .arg("--latencies")
        .arg("10,20,30")
        .arg("--threshold")
        .arg("20.0");

    cmd.assert()
        .success()
        // 改行付きで "a,b\n" が出力されること
        .stdout(predicate::eq("a,b\n"));
}
