// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\tests\test_vrf.rs
//! Integration tests for vrf_rust

use vrf_rust::keypair::generate_vrf_keypair_py;
use vrf_rust::prover::prove_vrf_py;
use vrf_rust::verifier::verify_vrf_py;

#[test]
fn test_vrf_roundtrip() {
    // 1) キーペア生成
    let (pk, sk) = generate_vrf_keypair_py().expect("keypair generation failed");
    let message = b"hello vrf";

    // 2) 証明とハッシュ取得
    let (proof, hash1) = prove_vrf_py(sk.clone(), message.to_vec())
        .expect("proof generation failed");

    // 3) 検証して同じハッシュが返ること
    let hash2 = verify_vrf_py(pk.clone(), proof.clone(), message.to_vec())
        .expect("verification failed");
    assert_eq!(hash1, hash2, "VRF hash mismatch");
}

#[test]
fn test_vrf_bad_proof() {
    let (pk, sk) = generate_vrf_keypair_py().expect("keypair generation failed");
    let message = b"test bad proof";

    // 正常な証明生成
    let (mut proof, _hash) = prove_vrf_py(sk.clone(), message.to_vec())
        .expect("proof generation failed");

    // 証明をちょっと改ざん
    proof[0] ^= 0xFF;

    // 検証時にエラーとなること
    let result = verify_vrf_py(pk.clone(), proof, message.to_vec());
    assert!(result.is_err(), "Malformed proof must not verify");
}
