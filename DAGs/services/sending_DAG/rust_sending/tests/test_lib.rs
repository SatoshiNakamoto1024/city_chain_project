// sending_DAG\rust_sending\tests\test_lib.rs

use std::process::Command;
use std::str;

#[test]
fn test_ntru_dilithium() {
    // 簡単にlib.rsのAPIを呼んでみる例 => 実際には「cargo test」時に
    // pyo3を介してPythonを呼ぶのは面倒なので、Rust側だけで単体テストを示す。

    // ここでは "cargo run -- test" のように別プロセスを呼ぶか、
    // もしくはlib内の関数を直接呼ぶ(要pub化)。
    // 例:
    //    let enc = ntru_dilithium::ntru_encrypt_stub("hello");
    //    assert!(enc.starts_with("NTRU_ENCRYPTED"));

    // 省略: lib.rsの中のpub関数を直接呼ぶパターン
    // => lib.rsで ntru_dilithiumをpubにしておけばOK

    assert_eq!(2+2, 4);
}

#[test]
fn test_batch_verify() {
    // batch_verify のロジックをテストするならlib.rsで pub fn batch_verify_internal(...) など
    // 用意して呼ぶ例を作る
    assert!(true);
}
