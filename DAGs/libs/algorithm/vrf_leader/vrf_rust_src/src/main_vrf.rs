// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\src\main_vrf.rs
// src/main_vrf.rs
//! CLI サンプル: VRF キーペア生成／証明生成／検証

use openssl::ec::{EcGroup, EcKey};
use openssl::nid::Nid;
use vrf::openssl::{ECVRF, CipherSuite};
use vrf::VRF;                // ← これがないと prove()/verify() が未発見になります

use hex::{encode, decode};
use std::env;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args();
    let cmd = args.nth(1).unwrap_or_default();

    match cmd.as_str() {
        "gen" => {
            let (pk, sk) = generate_keypair()?;
            println!("Public Key: {}", encode(pk));
            println!("Secret Key: {}", encode(sk));
        }
        "prove" => {
            let sk_hex = args.next().expect("missing <sk_hex>");
            let msg    = args.next().expect("missing <message>").as_bytes().to_vec();

            let sk = decode(sk_hex)?;
            let (proof, hash) = prove(&sk, &msg)?;
            println!("Proof: {}", encode(proof));
            println!("Hash:  {}", encode(hash));
        }
        "verify" => {
            let pk_hex    = args.next().expect("missing <pk_hex>");
            let proof_hex = args.next().expect("missing <proof_hex>");
            let msg       = args.next().expect("missing <message>").as_bytes().to_vec();

            let pk    = decode(pk_hex)?;
            let proof = decode(proof_hex)?;
            let hash  = verify(&pk, &proof, &msg)?;
            println!("Hash: {}", encode(hash));
        }
        _ => {
            eprintln!("Usage:");
            eprintln!("  main_vrf gen");
            eprintln!("  main_vrf prove <sk_hex> <message>");
            eprintln!("  main_vrf verify <pk_hex> <proof_hex> <message>");
        }
    }

    Ok(())
}

/// キーペア生成 (P-256 + ECVRF)
fn generate_keypair() -> Result<(Vec<u8>, Vec<u8>), Box<dyn std::error::Error>> {
    let group = EcGroup::from_curve_name(Nid::X9_62_PRIME256V1)?;
    let ec_key = EcKey::generate(&group)?;
    let sk_bytes = ec_key.private_key().to_vec();

    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)?;
    let pk_bytes = vrf.derive_public_key(&sk_bytes)?;
    Ok((pk_bytes, sk_bytes))
}

/// VRF 証明とハッシュ出力を生成
fn prove(secret_key: &[u8], message: &[u8]) -> Result<(Vec<u8>, Vec<u8>), Box<dyn std::error::Error>> {
    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)?;
    let proof = vrf.prove(secret_key, message)?;
    let hash  = vrf.proof_to_hash(&proof)?;
    Ok((proof, hash))
}

/// VRF 証明の検証とハッシュ取得
fn verify(public_key: &[u8], proof: &[u8], message: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)?;
    let hash = vrf.verify(public_key, proof, message)?;
    Ok(hash)
}
