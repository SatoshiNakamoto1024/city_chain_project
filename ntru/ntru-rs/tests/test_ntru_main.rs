// tests/test_ntru_main.rs

use ntrust_native::{
    CRYPTO_CIPHERTEXTBYTES, CRYPTO_PUBLICKEYBYTES, CRYPTO_SECRETKEYBYTES,
};
use ntru_rs::ntru_operations::{decrypt, encrypt, generate_keypair};

#[test]
fn test_ntru_keypair_generation() {
    let result = generate_keypair();
    assert!(result.is_ok());

    let keypair = result.unwrap();
    assert_eq!(keypair.public_key.len(), CRYPTO_PUBLICKEYBYTES);
    assert_eq!(keypair.secret_key.len(), CRYPTO_SECRETKEYBYTES); // 修正
}

#[test]
fn test_ntru_encryption_and_decryption() {
    let keypair = generate_keypair().expect("Failed to generate keypair");
    
    let (cipher_text, shared_secret) = encrypt(&keypair.public_key).expect("Encryption failed");
    assert_eq!(cipher_text.cipher_text.len(), CRYPTO_CIPHERTEXTBYTES); // 修正

    let decrypted_shared_secret = decrypt(&cipher_text.cipher_text, &keypair.secret_key).expect("Decryption failed");

    assert_eq!(shared_secret.shared_secret, decrypted_shared_secret.shared_secret);
}
