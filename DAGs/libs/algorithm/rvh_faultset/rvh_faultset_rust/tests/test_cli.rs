// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\tests\test_cli.rs
use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn cli_select_works() {
    let mut cmd = Command::cargo_bin("main_faultset").unwrap();
    cmd.arg("--nodes")
        .arg("a,b,c")
        .arg("--latencies")
        .arg("10,20,30")
        .arg("--threshold")
        .arg("20.0");
    cmd.assert()
        .success()
        .stdout(predicate::eq("a,b\n"));
}
