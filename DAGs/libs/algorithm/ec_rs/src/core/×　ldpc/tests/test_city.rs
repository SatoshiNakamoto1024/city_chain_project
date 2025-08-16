// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\tests\test_city.rs
//! City-DAG : dv=3,dc=6, circulant=32 ― 基本ラウンドトリップ確認
//! 1 MiB データ / パリティ 25 % 欠損

use ldpc::tiers::city;
use rand::Rng;

#[test]
fn city_roundtrip_1mib() {
    // ---- 1 MiB ランダムペイロード ----
    let mut rng = rand::thread_rng();
    let mut data = vec![0u8; 1 << 20];
    rng.fill(&mut data[..]);

    // ---- エンコード ----
    let shards = city::encode(&data);

    // ---- 25 % 欠損シミュレーション ----
    let mut opt: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
    let mut erased = 0;
    let max_erase = city::CFG.parity_shards / 4;
    for i in 0..opt.len() {
        if erased < max_erase && i % 7 == 0 {
            opt[i] = None;
            erased += 1;
        }
    }

    // ---- 復元 ----
    let recovered = city::decode(opt).expect("city decode failed");
    assert_eq!(&recovered[..data.len()], &data[..]);
}
