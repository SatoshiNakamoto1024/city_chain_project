// D:\city_chain_project\Algorithm\EC\ec_rust_src\tests\test_reed_solomon.rs
use crate::core::reed_solomon::ReedSolomonCoder;
use crate::ECConfig;
use crate::core::ErasureCoder;

#[test]
fn test_reed_solomon_basic_plugin() {
    // 設定を生成
    let cfg = ECConfig {
        data_shards: 2,
        parity_shards: 1,
        min_shard_size: 4,
        ..Default::default()
    };
    let coder = ReedSolomonCoder::new(&cfg).unwrap();

    let data = b"hello world";
    let shards = coder.encode(data, &cfg).unwrap();
    assert_eq!(shards.len(), 3);

    // 一部シャードを欠損させる
    let mut shards_opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    shards_opt[0] = None;

    // 復元
    let decoded = coder.decode(shards_opt, &cfg).unwrap();
    assert_eq!(&decoded[..data.len()], data);
    // min_shard_size でパディングされた部分は無視
}
