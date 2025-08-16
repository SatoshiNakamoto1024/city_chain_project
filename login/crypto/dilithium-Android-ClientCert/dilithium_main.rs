use dilithium5::{generate_keypair, sign, verify};

fn main() {
    // 鍵ペア生成
    let (public_key, secret_key) = match generate_keypair() {
        Ok(keys) => keys,
        Err(e) => {
            eprintln!("鍵ペアの生成に失敗しました: {:?}", e);
            return;
        }
    };

    println!("公開鍵の長さ: {} バイト", public_key.len());
    println!("秘密鍵の長さ: {} バイト", secret_key.len());

    // UTF-8エンコードされたメッセージを使用
    let message = "これはテストメッセージです".as_bytes();
    println!("署名対象のメッセージ: {:?}", String::from_utf8_lossy(message));
    println!("メッセージの長さ: {} バイト", message.len());

    // メッセージ署名
    let signed_message = match sign(message, &secret_key) {
        Ok(sm) => sm,
        Err(e) => {
            eprintln!("署名に失敗しました: {:?}", e);
            return;
        }
    };

    println!("署名付きメッセージの長さ: {} バイト", signed_message.len());

    // 署名検証
    let is_valid = match verify(message, &signed_message, &public_key) {
        Ok(valid) => valid,
        Err(e) => {
            eprintln!("署名検証に失敗しました: {:?}", e);
            return;
        }
    };

    if is_valid {
        println!("署名検証成功!");
    } else {
        println!("署名検証失敗...");
    }
}
