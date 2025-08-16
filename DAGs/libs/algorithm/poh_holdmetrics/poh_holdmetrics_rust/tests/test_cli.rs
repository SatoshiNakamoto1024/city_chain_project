// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_cli.rs
//! ビルド済みバイナリが正常終了するかを確認
use assert_cmd::Command;

#[test]
fn cli_runs_ok() {
    let mut cmd = Command::cargo_bin("main_holdmetrics").unwrap();
    // --help が 0 で返るだけでも OK
    cmd.arg("--help").assert().success();
}
