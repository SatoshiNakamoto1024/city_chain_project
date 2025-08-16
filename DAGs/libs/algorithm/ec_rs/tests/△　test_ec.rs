// D:\city_chain_project\Algorithm\EC\ec_rust_src\tests\test_ec.rs

use ec_rust::encode_rs;
use ec_rust::decode_rs;
use ec_rust::ECError;

#[test]
fn test_encode_decode_roundtrip() {
    let data = b"The quick brown fox jumps over the lazy dog";
    let n = 10;
    let k = 6;
    let shards = encode_rs(data, n, k).expect("encode failed");
    // 欠損をシミュレート
    let mut shards_opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    shards_opt[0] = None;
    shards_opt[3] = None;
    let recovered = decode_rs(&mut shards_opt, k).expect("decode failed");
    assert_eq!(recovered, data);
}

#[test]
fn test_invalid_params_encode() {
    let data = b"hello";
    // n < k のエラー
    match encode_rs(data, 3, 5) {
        Err(ECError::InvalidParams(3,5)) => {}
        other => panic!("Expected InvalidParams, got {:?}", other),
    }
}

#[test]
fn test_invalid_params_decode() {
    let data = b"foo";
    let shards = encode_rs(data, 5, 3).unwrap();
    let mut shards_opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    // 破壊数を超える欠損を生じさせる
    for i in 0..(5-3+1) {
        shards_opt[i] = None;
    }
    assert!(matches!(decode_rs(&mut shards_opt, 3), Err(ECError::RS(_))));
}
