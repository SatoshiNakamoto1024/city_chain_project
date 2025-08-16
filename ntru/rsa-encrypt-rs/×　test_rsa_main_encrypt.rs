extern crate base64;
extern crate rand;
extern crate rsa;

use base64::{decode, encode};
use rand::rngs::OsRng;
use rsa::{PaddingScheme, PublicKey, RsaPrivateKey, RsaPublicKey};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rsa_encryption_and_decryption() {
        // 1. 鍵の生成
        let mut rng = OsRng;
        let bits = 2048;
        let private_key = RsaPrivateKey::new(&mut rng, bits).expect("Failed to generate a key");
        let public_key = RsaPublicKey::from(&private_key);

        // 2. メッセージの暗号化
        let message = "Hello, RSA!";
        let encrypted_data = public_key
            .encrypt(
                &mut rng,
                PaddingScheme::new_pkcs1v15_encrypt(),
                &message.as_bytes(),
            )
            .expect("Failed to encrypt");

        // 暗号文をBase64でエンコード
        let encoded_encrypted_data = encode(&encrypted_data);

        // 3. 暗号文の復号化
        let decoded_encrypted_data = decode(&encoded_encrypted_data).expect("Failed to decode base64");
        let decrypted_data = private_key
            .decrypt(
                PaddingScheme::new_pkcs1v15_encrypt(),
                &decoded_encrypted_data,
            )
            .expect("Failed to decrypt");

        // 復号化されたメッセージを文字列に変換
        let decrypted_message = String::from_utf8(decrypted_data).expect("Failed to convert to string");

        // 4. テスト: 復号化されたメッセージが元のメッセージと一致することを確認
        assert_eq!(decrypted_message, message, "Decrypted message does not match the original");
    }
}
