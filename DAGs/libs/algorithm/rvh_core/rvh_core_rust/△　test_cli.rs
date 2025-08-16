// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\tests\test_cli.rs
// tests/test_cli.rs
use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn cli_select_works() {
    // `cargo test` 時は target/debug に出来る
    let mut cmd = Command::cargo_bin("main_rvh").expect("binary exists");
    cmd.args(&[
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
        .stdout(predicate::str::is_match(r"(alpha|beta|gamma),(alpha|beta|gamma)")
            .unwrap());
}
