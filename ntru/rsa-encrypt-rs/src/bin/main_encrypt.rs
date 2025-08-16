extern crate rsa_encrypt_rs;

use rsa_encrypt_rs::{decrypt_message, encrypt_message, generate_keypair};

fn main() {
    println!("Connecting to Blockchain Main Chain...");

    // 1. RSA鍵ペアを生成
    let bits = 2048;
    let (private_key, public_key) = generate_keypair(bits);
    println!("RSA Key Pair generated successfully!");

    // 2. メッセージの暗号化と送信（仮実装）
    let message = "Transaction: Send 100 LoveTokens to UserB";
    println!("Original message to encrypt: {}", message);

    let encrypted_message = encrypt_message(&public_key, message);
    println!("Encrypted message (Base64): {}", encrypted_message);

    // 3. ブロックチェーン上での処理（仮想的に表示）
    println!("Sending encrypted transaction to Blockchain Main Chain...");
    println!("Encrypted transaction received and stored successfully.");

    // 4. メッセージの復号化（仮実装）
    println!("Decrypting transaction on Blockchain Main Chain...");
    let decrypted_message = decrypt_message(&private_key, &encrypted_message);
    println!("Decrypted transaction: {}", decrypted_message);

    // 仮の成功メッセージ
    println!("Transaction processed successfully on Blockchain Main Chain!");
}
