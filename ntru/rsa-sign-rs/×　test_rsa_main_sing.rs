extern crate base64;
extern crate rand;
extern crate rsa;
extern crate sha2;

use base64::{decode, encode};
use rand::rngs::OsRng;
use rsa::{PaddingScheme, PublicKey, RsaPrivateKey, RsaPublicKey};
use sha2::{Digest, Sha256};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rsa_signing_and_verification() {
        // 1. 鍵の生成
        let mut rng = OsRng;
        let bits = 2048;
        let private_key = RsaPrivateKey::new(&mut rng, bits).expect("Failed to generate a key");
        let public_key = RsaPublicKey::from(&private_key);

        // 2. メッセージのハッシュ値の計算
        let message = "Hello, RSA!";
        let mut hasher = Sha256::new();
        hasher.update(message);
        let hashed = hasher.finalize();

        // 3. 署名の生成
        let signature = private_key
            .sign(
                PaddingScheme::new_pkcs1v15_sign(Some(rsa::Hash::SHA2_256)),
                &hashed,
            )
            .expect("Failed to sign");

        // 署名をBase64でエンコード
        let encoded_signature = encode(&signature);

        // 4. 署名の検証
        let decoded_signature = decode(&encoded_signature).expect("Failed to decode base64");
        match public_key.verify(
            PaddingScheme::new_pkcs1v15_sign(Some(rsa::Hash::SHA2_256)),
            &hashed,
            &decoded_signature,
        ) {
            Ok(_) => assert!(true, "Signature is valid."),
            Err(_) => panic!("Signature verification failed."),
        }
    }

    #[test]
    fn test_invalid_signature() {
        // 1. 鍵の生成
        let mut rng = OsRng;
        let bits = 2048;
        let private_key = RsaPrivateKey::new(&mut rng, bits).expect("Failed to generate a key");
        let public_key = RsaPublicKey::from(&private_key);

        // 2. メッセージのハッシュ値の計算
        let message = "Hello, RSA!";
        let mut hasher = Sha256::new();
        hasher.update(message);
        let hashed = hasher.finalize();

        // 3. 署名の生成
        let signature = private_key
            .sign(
                PaddingScheme::new_pkcs1v15_sign(Some(rsa::Hash::SHA2_256)),
                &hashed,
            )
            .expect("Failed to sign");

        // 署名をBase64でエンコード
        let encoded_signature = encode(&signature);

        // 4. 無効な署名の検証（内容を改変）
        let mut invalid_signature = decode(&encoded_signature).expect("Failed to decode base64");
        invalid_signature[0] ^= 0xFF; // 最初のバイトを変更して無効にする
        match public_key.verify(
            PaddingScheme::new_pkcs1v15_sign(Some(rsa::Hash::SHA2_256)),
            &hashed,
            &invalid_signature,
        ) {
            Ok(_) => panic!("Invalid signature passed verification."),
            Err(_) => assert!(true, "Invalid signature verification correctly failed."),
        }
    }
}
