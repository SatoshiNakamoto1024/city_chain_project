// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\tests\test_import.rs
//! 「Python サブプロセスから import できるか」シンプルチェック

use assert_cmd::Command;
use predicates::str::contains;
use std::env;

#[test]
fn python_import_only() {
    let py = env::var("PYTHON_SYS_EXECUTABLE").unwrap_or_else(|_| "python".to_string());

    Command::new(py)
        .arg("-c")
        .arg("import rvh_faultset_rust, sys; print('import OK')")
        .assert()
        .success()
        .stdout(contains("import OK"));
}
