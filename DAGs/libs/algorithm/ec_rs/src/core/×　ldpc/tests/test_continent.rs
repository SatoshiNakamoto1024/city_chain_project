// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\tests\test_continent.rs
//! Continent-DAG : Min-Sum 8 iter & early stop
//! 2 MiB データ / パリティ 30 % 欠損

use ldpc::tiers::continent;
use rand::Rng;

#[test]
fn continent_roundtrip_2mib() {
    let mut rng = rand::thread_rng();
    let mut data = vec![0u8; 2 << 20];
    rng.fill(&mut data[..]);

    let shards = continent::encode(&data);

    // ­–– 約 30 % 欠損
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    for i in 0..opt.len() {
        if i % 6 == 0 { opt[i] = None; }
    }

    let recovered = continent::decode(opt).expect("continent decode failed");
    assert_eq!(&recovered[..data.len()], &data[..]);
}
