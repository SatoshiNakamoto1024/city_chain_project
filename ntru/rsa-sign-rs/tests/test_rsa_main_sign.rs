use rsa_sign_rs::{generate_keypair, sign_message, verify_signature};

#[test]
fn test_rsa_signing_and_verification() {
    let bits = 2048;

    // 鍵ペアの生成
    let (private_key, public_key) = generate_keypair(bits);

    // メッセージ
    let message = "Hello, RSA!";

    // 署名の生成
    let signature = sign_message(&private_key, message);

    // 署名の検証
    assert!(
        verify_signature(&public_key, message, &signature),
        "Signature verification failed"
    );
}

#[test]
fn test_invalid_signature() {
    let bits = 2048;

    // 鍵ペアの生成
    let (private_key, public_key) = generate_keypair(bits);

    // メッセージ
    let message = "Hello, RSA!";
    let invalid_message = "Goodbye, RSA!";

    // 署名の生成
    let signature = sign_message(&private_key, message);

    // 無効な署名の検証
    assert!(
        !verify_signature(&public_key, invalid_message, &signature),
        "Invalid signature verification passed"
    );
}
