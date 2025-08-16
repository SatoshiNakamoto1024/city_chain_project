use ntrust_native::CRYPTO_PUBLICKEYBYTES;
use ntru_rs::ntru_operations::{decrypt, encrypt, generate_keypair}; // クレート名を使用

fn main() {
    match run_example() {
        Ok(_) => println!("NTRU operations completed successfully."),
        Err(e) => eprintln!("Error during NTRU operations: {:?}", e),
    }
}

fn run_example() -> Result<(), Box<dyn std::error::Error>> {
    // Generate NTRU keypair
    let keypair = generate_keypair()?;
    println!("Public Key: {:?}", &keypair.public_key[..10]); // Partial display for brevity
    println!("Secret Key: {:?}", &keypair.secret_key[..10]);

    // Encrypt using the public key
    let (cipher_text, shared_secret) = encrypt(&keypair.public_key)?;
    println!("Cipher Text: {:?}", &cipher_text.cipher_text[..10]); // Partial display for brevity
    println!("Shared Secret: {:?}", &shared_secret.shared_secret[..10]);

    // Decrypt using the secret key
    let decrypted_shared_secret = decrypt(&cipher_text.cipher_text, &keypair.secret_key)?;
    println!("Decrypted Shared Secret: {:?}", &decrypted_shared_secret.shared_secret[..10]);

    // Validate shared secrets match
    if shared_secret.shared_secret == decrypted_shared_secret.shared_secret {
        println!("Shared secret validation successful!");
    } else {
        println!("Shared secret validation failed!");
    }

    Ok(())
}
