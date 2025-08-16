// D:\city_chain_project\Algorithm\EC\ec_rust_src\tests\test_sharding.rs
//! Integration tests for the high‐level `encode_rs`/`decode_rs` API.

use ec_rust::sharding::{encode_rs, decode_rs};

#[test]
fn test_sharding_roundtrip() {
    let data = b"The quick brown fox jumps over the lazy dog".to_vec();

    // Split into 3 data + 2 parity shards
    let shards = encode_rs(&data, 3, 2).expect("encode failed");
    assert_eq!(shards.len(), 5);

    // Simulate a missing shard
    let mut shards_opt: Vec<Option<Vec<u8>>> =
        shards.into_iter().map(Some).collect();
    shards_opt[2] = None;

    // Reconstruct and compare
    let recovered = decode_rs(shards_opt, 3, 2).expect("decode failed");
    assert_eq!(&recovered[..data.len()], &data[..]);
}

#[test]
fn test_sharding_missing_too_many() {
    let data = vec![0u8; 1000];
    let shards = encode_rs(&data, 4, 2).unwrap();

    // Remove three shards (exceeds parity=2)
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    opt[1] = None;
    opt[3] = None;
    opt[5] = None;

    // Should error
    assert!(decode_rs(opt, 4, 2).is_err());
}

#[test]
fn test_sharding_out_of_order() {
    let data = b"edge-case".to_vec();
    let mut shards = encode_rs(&data, 2, 2).unwrap();
    // Swap slice order
    shards.swap(0, 2);
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    opt[1] = None; // drop one
    let rec = decode_rs(opt, 2, 2).unwrap();
    assert_eq!(&rec[..data.len()], &data[..]);
}
