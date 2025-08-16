// D:\city_chain_project\Algorithm\EC\ec_rust_src\tests\test_cli.rs
use assert_cmd::Command;
use predicates::prelude::*;
use std::fs;
use tempfile::tempdir;

#[test]
fn test_cli_encode_and_decode() {
    let dir = tempdir().unwrap();
    let input = dir.path().join("in.txt");
    fs::write(&input, b"hello world").unwrap();
    let shards_dir = dir.path().join("shards");
    let output = dir.path().join("out.txt");

    // encode
    Command::cargo_bin("ec_rust").unwrap()
        .args(&[
            "encode",
            "--input",  input.to_str().unwrap(),
            "--output", shards_dir.to_str().unwrap(),
            "--data-shards", "2",
            "--parity-shards", "1",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("Encoded 2 data shards and 1 parity shards"));

    // decode
    Command::cargo_bin("ec_rust").unwrap()
        .args(&[
            "decode",
            "--input",  shards_dir.to_str().unwrap(),
            "--output", output.to_str().unwrap(),
            "--data-shards", "2",
            "--parity-shards", "1",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("Decoded original data to"));

    // verify content
    let recovered = fs::read(&output).unwrap();
    assert_eq!(&recovered, b"hello world");
}
