// D:\city_chain_project\ntru\rsa-sign-rs\src\lib.rs
use rsa::{PaddingScheme, PublicKey, RsaPrivateKey, RsaPublicKey};
use sha2::{Digest, Sha256};
use base64::{decode, encode};
use rand::rngs::OsRng;

pub fn generate_keypair(bits: usize) -> (RsaPrivateKey, RsaPublicKey) {
    let mut rng = OsRng;
    let private_key = RsaPrivateKey::new(&mut rng, bits).expect("Failed to generate a key");
    let public_key = RsaPublicKey::from(&private_key);
    (private_key, public_key)
}

pub fn sign_message(private_key: &RsaPrivateKey, message: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(message);
    let hashed = hasher.finalize();

    let signature = private_key
        .sign(
            PaddingScheme::new_pkcs1v15_sign(Some(rsa::Hash::SHA2_256)),
            &hashed,
        )
        .expect("Failed to sign");

    encode(&signature) // Base64 エンコードして返す
}

pub fn verify_signature(
    public_key: &RsaPublicKey,
    message: &str,
    encoded_signature: &str,
) -> bool {
    let mut hasher = Sha256::new();
    hasher.update(message);
    let hashed = hasher.finalize();

    let decoded_signature = decode(encoded_signature).expect("Failed to decode base64");
    public_key
        .verify(
            PaddingScheme::new_pkcs1v15_sign(Some(rsa::Hash::SHA2_256)),
            &hashed,
            &decoded_signature,
        )
        .is_ok()
}
