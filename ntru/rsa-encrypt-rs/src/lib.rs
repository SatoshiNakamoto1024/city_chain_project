extern crate base64;
extern crate rand;
extern crate rsa;

use base64::{decode, encode};
use rand::rngs::OsRng;
use rsa::{PaddingScheme, PublicKey, RsaPrivateKey, RsaPublicKey};

/// RSA鍵ペアを生成する関数
pub fn generate_keypair(bits: usize) -> (RsaPrivateKey, RsaPublicKey) {
    let mut rng = OsRng;
    let private_key = RsaPrivateKey::new(&mut rng, bits).expect("Failed to generate a key");
    let public_key = RsaPublicKey::from(&private_key);
    (private_key, public_key)
}

/// メッセージを暗号化する関数
pub fn encrypt_message(public_key: &RsaPublicKey, message: &str) -> String {
    let mut rng = OsRng;
    let encrypted_data = public_key
        .encrypt(
            &mut rng,
            PaddingScheme::new_pkcs1v15_encrypt(),
            &message.as_bytes(),
        )
        .expect("Failed to encrypt");
    encode(&encrypted_data) // Base64エンコードして返す
}

/// 暗号文を復号化する関数
pub fn decrypt_message(private_key: &RsaPrivateKey, encoded_encrypted_data: &str) -> String {
    let decoded_encrypted_data = decode(encoded_encrypted_data).expect("Failed to decode base64");
    let decrypted_data = private_key
        .decrypt(
            PaddingScheme::new_pkcs1v15_encrypt(),
            &decoded_encrypted_data,
        )
        .expect("Failed to decrypt");
    String::from_utf8(decrypted_data).expect("Failed to convert to string") // 復号化されたメッセージを返す
}
