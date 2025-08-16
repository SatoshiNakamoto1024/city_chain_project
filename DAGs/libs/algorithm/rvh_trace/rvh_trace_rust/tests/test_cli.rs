// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\tests\test_cli.rs

use assert_cmd::Command;          // 実行用
use predicates::prelude::*;       // 追加したクレート

#[test]
fn test_cli_runs() {
    let mut cmd = Command::cargo_bin("main_trace").unwrap();
    cmd.assert()
       .success()
       .stdout(predicates::str::contains("hello from CLI"));
}
