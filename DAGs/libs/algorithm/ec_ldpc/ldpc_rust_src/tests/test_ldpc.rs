// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\tests\test_ldpc.rs

// パッケージ名でインポートする
use ldpc::{LDPCEncoder, LDPCDecoder, ErasureCoder};

#[test]
fn test_multiple_erasure_recovery() {
    let data = (0u8..200).collect::<Vec<u8>>();
    let k = 5;
    let m = 3;
    let enc = LDPCEncoder::new();
    let shards = enc.encode(&data, k, m).unwrap();
    assert_eq!(shards.len(), k + m);

    // ２つ欠損させて復元
    let mut opt = shards.into_iter().map(Some).collect::<Vec<_>>();
    opt[1] = None;
    opt[3] = None;

    let dec = LDPCDecoder::new();
    let recovered = dec.decode(opt, k, m).unwrap();
    assert_eq!(&recovered[..data.len()], &data[..]);
}