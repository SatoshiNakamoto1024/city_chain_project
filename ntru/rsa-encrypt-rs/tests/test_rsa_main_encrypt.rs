extern crate rsa_encrypt_rs;

use base64::{decode, encode};
use rsa_encrypt_rs::{decrypt_message, encrypt_message, generate_keypair};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rsa_encryption_and_decryption() {
        // 1. 鍵ペアの生成
        let bits = 2048;
        let (private_key, public_key) = generate_keypair(bits);

        // 2. メッセージの暗号化
        let message = "Hello, RSA Encryption!";
        let encrypted_message = encrypt_message(&public_key, message);

        // 3. 暗号化されたメッセージの検証
        assert!(!encrypted_message.is_empty(), "Encrypted message should not be empty.");

        // 4. メッセージの復号化
        let decrypted_message = decrypt_message(&private_key, &encrypted_message);

        // 5. 復号化されたメッセージの検証
        assert_eq!(decrypted_message, message, "Decrypted message does not match the original.");
    }

    #[test]
    fn test_invalid_decryption() {
        // 1. 鍵ペアの生成
        let bits = 2048;
        let (private_key, public_key) = generate_keypair(bits);

        // 2. メッセージの暗号化
        let message = "Hello, RSA Encryption!";
        let encrypted_message = encrypt_message(&public_key, message);

        // 3. 別の鍵ペアを生成して復号を試みる
        let (other_private_key, _) = generate_keypair(bits);
        let result = std::panic::catch_unwind(|| decrypt_message(&other_private_key, &encrypted_message));

        // 4. 復号化が失敗することを確認
        assert!(result.is_err(), "Decryption should fail with the wrong private key.");
    }
}
