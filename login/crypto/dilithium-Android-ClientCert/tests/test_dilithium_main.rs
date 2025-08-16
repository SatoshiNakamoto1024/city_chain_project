#[cfg(test)]
mod tests {
    use dilithium5::{generate_keypair, sign, verify};

    #[test]
    fn test_generate_keypair() {
        let (public_key, secret_key) = generate_keypair().expect("鍵ペアの生成に失敗");
        assert!(!public_key.is_empty());
        assert!(!secret_key.is_empty());
    }

    #[test]
    fn test_sign_and_verify() {
        let (public_key, secret_key) = generate_keypair().expect("鍵ペアの生成に失敗");
        let message = "テストメッセージ".as_bytes(); // バイト列に変換
        let wrong_message = "不正なメッセージ".as_bytes(); // バイト列に変換
        let signed_message = sign(message, &secret_key).expect("署名に失敗");
        let is_valid = verify(message, &signed_message, &public_key).expect("署名検証に失敗");
        assert!(is_valid, "署名検証に失敗しました");
    }

    #[test]
    fn test_invalid_signature() {
        // テスト用のメッセージ
        let message = "テストメッセージ".as_bytes(); // バイト列に変換
        let wrong_message = "不正なメッセージ".as_bytes(); // バイト列に変換

        // 鍵ペアの生成
        let (public_key, secret_key) = generate_keypair().expect("鍵ペアの生成に失敗しました");

        // 正しいメッセージの署名
        let signed_message = sign(message, &secret_key).expect("メッセージの署名に失敗しました");

        // 不正なメッセージを使用した検証
        let is_valid = verify(wrong_message, &signed_message, &public_key).expect("署名の検証に失敗しました");
        assert!(!is_valid, "不正なメッセージの検証が成功してしまいました");

        println!("不正な署名検証テスト成功: メッセージ='{}'", String::from_utf8_lossy(wrong_message));
    }
}
