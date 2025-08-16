// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\tests\test_global.rs
//! Global-DAG : Sum-Product BP → RS フォールバック
//! 4 MiB データ / 欠損 40 % 以内

use ldpc::tiers::global;
use rand::Rng;

#[test]
fn global_roundtrip_4mib() {
    let mut rng = rand::thread_rng();
    let mut data = vec![0u8; 4 << 20];
    rng.fill(&mut data[..]);

    let shards = global::encode(&data);

    // ---- 40 % 欠損（BP が失敗しても RS で復元できる範囲） ----
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    let m = global::CFG.parity_shards;
    for i in 0..(m * 4 / 10) {        // parity 域中心に消す
        opt[global::CFG.data_shards + i] = None;
    }

    let recovered = global::decode(opt).expect("global decode failed");
    assert_eq!(&recovered[..data.len()], &data[..]);
}
