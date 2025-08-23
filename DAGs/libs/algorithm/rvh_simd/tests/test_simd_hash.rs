// D:\city_chain_project\DAGs\libs\algorithm\rvh_simd\tests\test_simd_hash.rs
use rvh_simd::score_u128_simd;

#[test]
fn determinism() {
    let a = score_u128_simd("nodeX", "keyY").unwrap();
    let b = score_u128_simd("nodeX", "keyY").unwrap();
    assert_eq!(a, b);
}

#[test]
fn different_inputs() {
    let a = score_u128_simd("nodeX", "keyY").unwrap();
    let b = score_u128_simd("nodeX", "keyZ").unwrap();
    assert_ne!(a, b);
}
