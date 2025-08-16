extern crate rsa_sign_rs;

use rsa_sign_rs::{generate_keypair, sign_message, verify_signature};

fn main() {
    let bits = 2048;

    // 鍵ペアの生成
    let (private_key, public_key) = generate_keypair(bits);
    println!("Private Key: {:?}", private_key);
    println!("Public Key: {:?}", public_key);

    // メッセージ
    let message = "Hello, RSA!";
    println!("Original message: {}", message);

    // 署名の生成
    let signature = sign_message(&private_key, message);
    println!("Signature: {}", signature);

    // 署名の検証
    if verify_signature(&public_key, message, &signature) {
        println!("Signature is valid.");
    } else {
        println!("Signature is invalid.");
    }
}
