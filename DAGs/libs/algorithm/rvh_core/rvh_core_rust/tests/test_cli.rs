// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\tests\test_cli.rs
//! CLI round-trip test

use assert_cmd::Command;
use predicates::str::is_match;

#[test]
fn cli_select_works() {
    // バイナリ名は Cargo.toml に合わせる
    let mut cmd = Command::cargo_bin("main_rvh_core").expect("binary exists");
    cmd.args([
        "select",
        "--nodes",
        "alpha,beta,gamma",
        "--key",
        "file-42",
        "--k",
        "2",
    ]);
    cmd.assert()
        .success()
        .stdout(is_match(r"(alpha|beta|gamma),(alpha|beta|gamma)").unwrap());
}
